import io
import zipfile
from parser.snakemake_parser import SnakemakeParser

import pytest


@pytest.fixture
def sample_snakefile_content() -> str:
    """Provides a simple but complete Snakefile with dependencies."""
    return """
rule all:
    input: "results/final_report.txt"
rule map_reads:
    input: "data/{sample}.fastq"
    output: "results/mappings/{sample}.bam"
    shell: "bwa mem ref.fa {input} > {output}"
rule call_variants:
    input: "results/mappings/{sample}.bam"
    output: "results/variants/{sample}.vcf"
    shell: "samtools mpileup -uf ref.fa {input} | bcftools call -mv > {output}"
rule generate_report:
    input: "results/variants/A.vcf", "results/variants/B.vcf"
    output: "results/final_report.txt"
    shell: "echo 'Report generated' > {output}"
"""


@pytest.fixture
def sample_config_yaml_content() -> str:
    """Provides a config file that defines the 'sample' wildcard."""
    return """
wildcards:
    sample:
        - A
        - B
"""


@pytest.fixture
def sample_zip_file_bytes(
    sample_snakefile_content, sample_config_yaml_content
) -> bytes:
    """Creates an in-memory ZIP file containing the Snakefile and config."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("workflow/Snakefile", sample_snakefile_content)
        zip_file.writestr("config/config.yaml", sample_config_yaml_content)
    zip_buffer.seek(0)
    return zip_buffer.read()


class TestSnakemakeParser:
    """Test suite for the SnakemakeParser."""

    # TODO: fix this test
    # def test_parse_zip_file_and_builds_correct_dependency_graph(
    #     self, sample_zip_file_bytes: bytes
    # ):
    #    """
    #    GIVEN a ZIP file with a Snakefile and a config file
    #    WHEN the parser's parse method is called
    #    THEN it should return a Workflow with correctly resolved wildcards and dependencies.
    #    """
    #    parser = SnakemakeParser()
    #    workflow = parser.parse(file_content_bytes=sample_zip_file_bytes, filename="workflow.zip")

    #    assert isinstance(workflow, Workflow)
    #    assert len(workflow.tasks) == 5

    #    jobs_by_name = {job.name: job for job in workflow.tasks}
    #    map_reads = jobs_by_name["map_reads"]
    #    call_variants = jobs_by_name["call_variants"]
    #    generate_report = jobs_by_name["generate_report"]

    #    assert len(call_variants.dependencies) == 1
    #    assert map_reads in call_variants.dependencies

    #    assert len(generate_report.dependencies) == 1
    #    assert call_variants in generate_report.dependencies

    def test_parse_single_snakefile_without_config(self):
        """
        GIVEN a single Snakefile without wildcards in the dependencies
        WHEN the parse method is called
        THEN it should correctly parse the dependencies.
        """
        simple_snakefile = b"""
rule all:
    input: "c.txt"
rule B:
    input: "a.txt"
    output: "b.txt"
    shell: "touch {output}"
rule C:
    input: "b.txt"
    output: "c.txt"
    shell: "touch {output}"
"""
        parser = SnakemakeParser()
        workflow = parser.parse(
            file_content_bytes=simple_snakefile, filename="Snakefile"
        )

        assert len(workflow.tasks) == 2
        job_b = next(j for j in workflow.tasks if j.name == "B")
        job_c = next(j for j in workflow.tasks if j.name == "C")

        assert len(job_b.dependencies) == 0
        assert len(job_c.dependencies) == 1
        assert job_b in job_c.dependencies

    def test_parse_raises_error_for_unsupported_file_type(self):
        """
        GIVEN a file with an unsupported extension (e.g., .txt)
        WHEN the parser's parse method is called
        THEN a ValueError should be raised.
        """
        parser = SnakemakeParser()
        with pytest.raises(ValueError, match="Unsupported file type: txt"):
            parser.parse(file_content_bytes=b"some content", filename="file.txt")
