import logging
import shlex
from typing import Any, Dict, Optional
from uuid import uuid4

from db.models import HPCJob, TaskStatus, Workflow, WorkflowStatus

from .base import AbstractWorkflowParser
from .registry import ParserRegistry

logger = logging.getLogger(__name__)


@ParserRegistry.register
class SlurmSbatchParser(AbstractWorkflowParser):
    """
    Parses a SLURM sbatch script to create a single-task Workflow.

    This parser creates an 'HPCJob' task and stores the *entire*
    sbatch script content in the 'command_str' field.

    It uses `shlex` to robustly parse #SBATCH directives and standard
    string manipulation for resource values (Memory/GPU), avoiding Regex.
    """

    @classmethod
    def can_parse(cls, filename: str, file_content: bytes) -> bool:
        """
        Returns True if the file has a .sbatch extension or looks like
        a shell script starting with #!/bin/bash and containing #SBATCH.
        """
        name = filename.lower()
        if name.endswith((".sbatch", ".slurm")):
            return True

        # Fallback: check content for shebang and #SBATCH
        try:
            content_str = file_content.decode("utf-8").lstrip()
            return content_str.startswith("#!/bin/bash") and "#SBATCH" in content_str
        except Exception:
            return False

    def _parse_memory_string(self, value: str) -> Optional[str]:
        """
        Parses Slurm memory strings (e.g., '4G', '100MB', '1024') into a
        normalized 'M' (Megabyte) string format (e.g., '4096M').
        """
        if not value:
            return None

        # Normalize: strip whitespace, uppercase, remove trailing 'B'
        # e.g., " 4Gb " -> "4G"
        cleaned = value.strip().upper()
        if cleaned.endswith("B"):
            cleaned = cleaned[:-1]

        if not cleaned:
            return None

        # Identify suffix
        suffix = cleaned[-1]
        number_part = cleaned[:-1]

        # If the last char is a digit, Slurm usually defaults to MB (Default)
        if suffix.isdigit():
            # Case: "1024" -> 1024M
            try:
                val = int(cleaned)
                return f"{val}M"
            except ValueError:
                return None

        # If last char is a unit suffix
        try:
            val = int(number_part)
        except ValueError:
            return None  # Malformed number

        if suffix == "M":
            return f"{val}M"
        elif suffix == "G":
            return f"{val * 1024}M"
        elif suffix == "T":
            return f"{val * 1024 * 1024}M"
        elif suffix == "K":
            # Round up to 1M if less than 1024K, otherwise convert
            return f"{max(1, val // 1024)}M"

        # Unknown suffix, return raw or None
        return None

    def _parse_gpu_count(self, value: str) -> Optional[int]:
        """
        Parses Slurm GRES/GPU strings to extract the count.
        Formats supported: "1", "gpu:1", "gpu:v100:1"
        """
        if not value:
            return None

        # Split by colon
        parts = value.split(":")

        # Logic: The count is usually the *last* segment if it is a pure integer.
        # e.g. "gpu:v100:2" -> ["gpu", "v100", "2"] -> last is "2"
        # e.g. "2"          -> ["2"]              -> last is "2"

        last_part = parts[-1].strip()

        if last_part.isdigit():
            return int(last_part)

        return None

    def _parse_sbatch_directives(self, content: str) -> Dict[str, Any]:
        """Extracts resource requests from #SBATCH lines."""
        extracted: Dict[str, Any] = {
            "name": None,
            "cpu": None,
            "mem": None,
            "gpu": None,
        }

        for line in content.splitlines():
            line = line.strip()
            if not line.startswith("#SBATCH"):
                continue

            # Remove the marker to get the arguments string
            # #SBATCH --nodes=1 -> --nodes=1
            args_str = line[7:].strip()

            try:
                # shlex.split handles quotes ("my job") and comments (#...) automatically
                tokens = shlex.split(args_str, comments=True)
            except ValueError:
                logger.warning(f"Failed to parse SBATCH line: {line}")
                continue

            i = 0
            while i < len(tokens):
                token = tokens[i]
                key = None
                value = None

                # Handle --key=value
                if "=" in token:
                    k_str, v_str = token.split("=", 1)
                    key = k_str.lstrip("-").lower()
                    value = v_str
                    i += 1
                # Handle --key value (or -k value)
                else:
                    key = token.lstrip("-").lower()
                    # Check if there is a next token that looks like a value
                    if i + 1 < len(tokens):
                        next_token = tokens[i + 1]
                        # Simple heuristic: if next token doesn't start with -, it's likely the value.
                        if not next_token.startswith("-"):
                            value = next_token
                            i += 2
                        else:
                            # The next token is another flag, so this flag has no value (boolean)
                            i += 1
                    else:
                        i += 1

                if not key or not value:
                    continue

                # Map extracted key/value to schema
                if key in ("job-name", "j"):
                    extracted["name"] = value
                elif key in ("cpus-per-task", "c"):
                    extracted["cpu"] = str(value)
                elif key in ("mem", "mem-per-cpu"):
                    mem_str = self._parse_memory_string(value)
                    if mem_str:
                        extracted["mem"] = mem_str
                elif key in ("gpus", "gpus-per-task", "gres"):
                    gpu_count = self._parse_gpu_count(value)
                    if gpu_count is not None:
                        extracted["gpu"] = gpu_count

        return extracted

    def parse(self, file_content_bytes: bytes, filename: str) -> Workflow:
        """
        Parses the sbatch file into a Workflow with one HPCJob task.
        """
        try:
            file_content = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"File '{filename}' is not valid UTF-8: {e}")

        # Extract directives to populate metadata
        directives = self._parse_sbatch_directives(file_content)
        job_name = directives.get("name") or filename

        # Create the single HPCJob
        workflow_id = uuid4()
        hpc_job = HPCJob(
            id=uuid4(),
            name=job_name,
            status=TaskStatus.WAITING,
            workflow_id=workflow_id,
            command_str=file_content,
            required_cpu=directives.get("cpu"),
            required_memory=directives.get("mem"),
            required_gpu=directives.get("gpu"),
            dependencies=[],
        )

        logger.info(
            f"Parsed '{filename}' into HPCJob '{hpc_job.name}' with "
            f"CPU='{hpc_job.required_cpu}', Mem='{hpc_job.required_memory}', GPU='{hpc_job.required_gpu}'"
        )

        # Wrap the single job in a Workflow
        workflow = Workflow(
            id=workflow_id,
            name=job_name,
            tasks=[hpc_job],
            status=WorkflowStatus.PENDING_DATA,
        )

        return workflow
