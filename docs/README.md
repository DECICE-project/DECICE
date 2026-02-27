# DECICE Admin Documentation
This documentation provides Site Reliability Engineers (SREs), DevOps teams, and system administrators with step-by-step guidance for deploying DECICE components on Kubernetes clusters and HPC nodes. It covers installation, configuration, and best practices for production environments.

## Deployment Overview
DECICE components are primarily deployed using Helm charts for Kubernetes, with the exception of the Slurm Client. The Slurm Client integrates HPC clusters into the DECICE framework and requires SLURM REST API endpoints to be configured. Since not all HPC centers enable SLURM REST APIs, the Slurm Client is provided as an optional component.


## Components
The following components are covered in this documentation:

- [Control Manager](./control-manager.md)
- [Digital Twin](./digital-twin.md)
- [AI Scheduler](./scheduler.md)
- [Platform Specific Glue Code](./psgc.md)
- [Scheduler Controller](./scheduler-controller.md)
- [PromQL-to-JSON Wrapper](./promql-wrapper.md)
- [WATMON](./watmon.md)
- [Web Interface](./frontend.md)
- [Slurm Client](./slurm-client.md)

## Documentation Structure
Each component guide includes:
- Helm chart installation instructions
- Configuration parameters
- Production deployment recommendations
