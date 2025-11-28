import textwrap
from parser import argo_parser, factory, k8s_parser, snakemake_parser

import pytest


def test_get_parser_argo_workflow():
    """Test that the factory returns ArgoYAMLParser for Argo Workflows."""
    argo_workflow_content = """
    apiVersion: argoproj.io/v1alpha1
    kind: Workflow
    metadata:
      name: test-workflow
    spec:
      entrypoint: main
    """
    parser = factory.get_parser(
        "workflow.yaml", textwrap.dedent(argo_workflow_content).encode("utf-8")
    )
    assert isinstance(parser, argo_parser.ArgoYAMLParser)


def test_get_parser_k8s_job():
    """Test that the factory returns K8sParser for Kubernetes Jobs."""
    k8s_job_content = """
    apiVersion: batch/v1
    kind: Job
    metadata:
      name: test-job
    """
    parser = factory.get_parser(
        "job.yaml", textwrap.dedent(k8s_job_content).encode("utf-8")
    )
    assert isinstance(parser, k8s_parser.K8sParser)


def test_get_parser_k8s_deployment():
    """Test that the factory returns K8sParser for Kubernetes Deployments."""
    k8s_deployment_content = """
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: test-deployment
    """
    parser = factory.get_parser(
        "deployment.yaml",
        textwrap.dedent(k8s_deployment_content).encode("utf-8"),
    )
    assert isinstance(parser, k8s_parser.K8sParser)


def test_get_parser_custom_resource_is_supported():
    """
    Test that the factory returns K8sParser for Custom Resources (Generic),
    verifying our permissive parsing update works.
    """
    custom_resource_content = """
    apiVersion: example.com/v1
    kind: CustomResource
    metadata:
        name: my-custom-resource
    """
    parser = factory.get_parser(
        "custom.yaml", textwrap.dedent(custom_resource_content).encode("utf-8")
    )
    assert isinstance(parser, k8s_parser.K8sParser)


def test_get_parser_snakemake_smk():
    """Test that the factory returns SnakemakeParser for .smk files."""
    parser = factory.get_parser("Snakefile.smk", b"rule all:\n  input: 'file.txt'")
    assert isinstance(parser, snakemake_parser.SnakemakeParser)


def test_get_parser_snakemake_zip():
    """Test that the factory returns SnakemakeParser for .zip files."""
    parser = factory.get_parser("workflow.zip", b"dummy zip content")
    assert isinstance(parser, snakemake_parser.SnakemakeParser)


def test_get_parser_unsupported_yaml_kind():
    """
    Test that the factory raises the generic error when no parser
    claims an otherwise valid YAML file.

    Updated to use 'Role', which is explicitly in IGNORED_TYPES.
    """
    unsupported_yaml_content = """
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
        name: my-role
    """

    with pytest.raises(
        ValueError, match="Unsupported file type or format for custom.yaml"
    ):
        factory.get_parser(
            "custom.yaml", textwrap.dedent(unsupported_yaml_content).encode("utf-8")
        )


def test_get_parser_missing_api_version_or_kind():
    """
    Test that the factory raises the generic error for a malformed YAML
    that no parser will claim.
    """
    missing_fields_yaml = """
    metadata:
        name: invalid
    """
    with pytest.raises(
        ValueError, match="Unsupported file type or format for invalid.yaml"
    ):
        factory.get_parser(
            "invalid.yaml", textwrap.dedent(missing_fields_yaml).encode("utf-8")
        )


def test_get_parser_invalid_yaml_format():
    """
    Test that the factory raises the generic error for fundamentally invalid YAML,
    as no parser's can_parse() will be able to load it.
    """
    invalid_yaml_content = b"this is not a valid yaml: -"
    with pytest.raises(
        ValueError, match="Unsupported file type or format for bad.yaml"
    ):
        factory.get_parser("bad.yaml", invalid_yaml_content)


def test_get_parser_unsupported_file_type():
    """
    Test that the factory raises the generic error for a file extension
    that no parser is registered to handle.
    """
    with pytest.raises(
        ValueError, match="Unsupported file type or format for document.txt"
    ):
        factory.get_parser("document.txt", b"some text")
