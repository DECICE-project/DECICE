import io
import os
import tempfile
from itertools import product
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4
from zipfile import ZipFile

import snakemake.cli
from snakemake.rules import Rule
from snakemake.settings.types import (ConfigSettings, DAGSettings,
                                      ResourceSettings, StorageSettings,
                                      WorkflowSettings)
from snakemake.workflow import Workflow as SnakeWF

from db.models import Job, TaskStatus, Workflow

from .base import AbstractWorkflowParser
from .registry import ParserRegistry


@ParserRegistry.register
class SnakemakeParser(AbstractWorkflowParser):
    def __init__(self):
        self.workflow = None
        self.rule_objects = {}

    @classmethod
    def can_parse(cls, filename: str, file_content: bytes) -> bool:
        name = filename.lower()
        return name.endswith((".zip", ".smk", ".snakefile")) or "snakefile" in name

    def initialize_workflow(self, snakefile: str, configfile: Optional[str]) -> None:
        """
        Creates Workflow object and stores Rule objects.

        Args:
            snakefile (str): Snakefile path.
            configfile (str): Configfile (config.yaml) path.

        Returns:
            None
        """
        self.workflow = SnakeWF(
            config_settings=(
                ConfigSettings(configfiles=[Path(configfile)])
                if configfile is not None
                else ConfigSettings(configfiles=[])
            ),
            resource_settings=ResourceSettings(),
            workflow_settings=WorkflowSettings(),
            storage_settings=StorageSettings(),
            dag_settings=DAGSettings(),
        )

        self.workflow.include(snakefile=snakefile)

        # Store rule objects of workflow for dependency steps
        for rule in self.workflow.rules:
            self.rule_objects[rule.name] = rule

    def extract_rules(self) -> list[dict[str, Any]]:
        """
        Creates rule metadata from Snakemake rules

        Args: None

        Returns:
            rules_metadata (list[dict[str, Any]]): list of dictionaries that contain rule information
        """
        if not self.workflow:
            raise ValueError("Workflow not initialized")

        rules_metadata = []
        for rule_name, rule_obj in self.rule_objects.items():
            rules_metadata.append(
                {
                    "name": rule_name,
                    "inputs": list(rule_obj.input),
                    "outputs": list(rule_obj.output),
                    "shell": getattr(rule_obj, "shellcmd", None),
                    "script": getattr(rule_obj, "script", None),
                    "container_image": getattr(rule_obj, "container_img", None),
                    "rule_wildcards": getattr(rule_obj, "wildcard_names", None),
                    "parameters": getattr(rule_obj, "params", None),
                    "config": self.workflow.config,
                    "dependencies": [],
                }
            )
        return rules_metadata

    def resolve_wildcards(self, rules: list) -> list[dict[str, Any]]:
        """
        Extract wildcards from config.yaml and resolves them for input/output fields

        Args: rules (list): list of rules including metadata

        Returns:
            rules (list[dict[str, Any]]): list of resolved rules and corresponding fields
        """
        # Wildcards can be in "input", "output" and "shell" parts. For now, we only work with "input" and "output" fields
        # TODO: How to resolve shell commands? Example:
        # rule complex_conversion:
        #    input:
        #        "{dataset}/inputfile"
        #    output:
        #        "{dataset}/file.{group}.txt"
        #    wildcard_constraints:
        #        dataset="\d+"
        #    shell:
        #        "somecommand --group {wildcards.group}  < {input}  > {output}"

        # The first rule in the list is generally named "all" and no need to resolve. Start from the second rule
        for rule in rules[1:]:
            config_wildcards = rule.get("config", {}).get("wildcards", {})
            wildcard_names = list(rule.get("rule_wildcards", []))
            wildcard_values = [config_wildcards[name] for name in wildcard_names]

            resolved_inputs = []
            resolved_outputs = []

            for combination in product(*wildcard_values) if wildcard_values else [()]:
                context = dict(zip(wildcard_names, combination))

                for pattern in rule.get("inputs", []):
                    if "{" in pattern:
                        resolved_inputs.append(pattern.format(**context))
                    else:
                        resolved_inputs.append(pattern)

                for pattern in rule.get("outputs", []):
                    if "{" in pattern:
                        resolved_outputs.append(pattern.format(**context))
                    else:
                        resolved_outputs.append(pattern)

            rule["inputs"] = resolved_inputs
            rule["outputs"] = resolved_outputs

        return rules[1:]

    def build_dependencies(self, rules: list) -> list[dict[str, Any]]:
        """
        Build dependencies by checking input/output files between rules

        Args: rules (list): list of rules including metadata

        Returns:
            rules (list[dict[str, Any]]): list of rules with dependencies
        """

        # Mapping between output file to producing rule name
        output_to_producer = {}
        for rule in rules:
            for output in rule["outputs"]:
                output_to_producer[output] = rule["name"]

        # For each rule, find dependencies based on input files
        # If their input is an output of another rule above, add that rule as dependency
        for rule in rules:
            deps = set()
            for input in rule["inputs"]:
                producer = output_to_producer.get(input)
                if producer is not None and producer != rule["name"]:
                    deps.add(producer)
            rule["dependencies"] = sorted(deps)
        return rules

    def write_to_tempfile(self, contents: str, suffix: str) -> str:
        """
        Writes Snakemake and its config file to temp files

        Args:
            contents (str): content of snake/config files
            suffix (str): extension of the file

        Returns:
            tmpf.name (str): path of file
        """
        tmpf = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
        tmpf.write(contents)
        tmpf.close()
        return tmpf.name

    def parse(self, file_content_bytes: bytes, filename: str) -> Workflow:
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        snakemake_content = None
        config_content = None

        if filename.lower() == "snakefile":
            extension = "smk"

        match extension:
            case "zip":
                with ZipFile(io.BytesIO(file_content_bytes)) as zip_ref:
                    file_list = zip_ref.namelist()
                    snakemake_file_name = None
                    config_file_name = None
                    for name in file_list:
                        file_basename = name.split("/")[-1]

                        if snakemake_file_name is None and (
                            name.endswith(".smk")
                            or file_basename.lower() == "snakefile"
                        ):
                            snakemake_file_name = name

                        if config_file_name is None and (
                            name.endswith(".yaml") or name.endswith(".yml")
                        ):
                            config_file_name = name
                        if snakemake_file_name and config_file_name:
                            break

                    if snakemake_file_name is None:
                        raise FileNotFoundError(
                            "Could not find Snakemake file in the ZIP"
                        )

                    with zip_ref.open(snakemake_file_name) as snakemake_file:
                        snakemake_content = snakemake_file.read().decode("utf-8")

                    if config_file_name is not None:
                        with zip_ref.open(config_file_name) as config_file:
                            config_content = config_file.read().decode("utf-8")
                    else:
                        config_content = None

                snakemake_path = self.write_to_tempfile(snakemake_content, ".smk")
                config_path = (
                    self.write_to_tempfile(config_content, ".yaml")
                    if config_content
                    else None
                )

            case "smk":
                snakemake_path = self.write_to_tempfile(
                    file_content_bytes.decode("utf-8"), ".smk"
                )
                config_path = None

            case _:
                raise ValueError(f"Unsupported file type: {extension}")

        self.initialize_workflow(snakefile=snakemake_path, configfile=config_path)
        rules = self.extract_rules()
        rules_with_wildcards = self.resolve_wildcards(rules)
        rules_with_deps = self.build_dependencies(rules_with_wildcards)

        workflow_id = uuid4()
        job_map = {}  # job_name -> Job object mapping
        all_jobs = []

        for rule in rules_with_deps:
            command = rule.get("script") or rule.get("shell")
            job = Job(
                id=uuid4(),
                name=rule.get("name", "snakemake-job"),
                status=TaskStatus.WAITING,
                image=rule.get("container_image", None),
                command_str=command,
                workflow_id=workflow_id,
                required_cpu="1",
                required_memory="128Mi",
                annotations={"dev.decice.com/storage-request": "1Gi"} 
            )
            job_map[job.name] = job
            all_jobs.append(job)

        for rule in rules_with_deps:
            job_name = rule["name"]
            job = job_map[job_name]

            dependencies = []
            for dep_name in rule.get("dependencies", []):
                if dep_name in job_map:
                    dependencies.append(job_map[dep_name])

            job.dependencies = dependencies

        workflow = Workflow(
            id=workflow_id,
            name=f"snakemake-{workflow_id}",
            tasks=all_jobs,
            status=TaskStatus.WAITING,
        )

        # Remove Snake/Config files from temp location
        os.remove(snakemake_path)
        if config_path is not None:
            os.remove(config_path)

        return workflow
