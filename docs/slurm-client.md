# Slurm Client

The Slurm Client in DECICE is a standalone component designed to integrate High Performance Computing (HPC) environments into the DECICE scheduling and orchestration framework.

By separating the client from the core DECICE components, this architecture:

- Allows HPC integration only when required (optional in cloud-only or edge-only deployments).
- Enables reuse of DECICE orchestration pipelines in mixed HPC / cloud / edge environments.
- Keeps sensitive HPC authentication logic localized to the HPC environment.

The Slurm Client has two core subcomponents:

HTTP API Server Provides REST API endpoints for:

- Job submission to Slurm
- Retrieval of user account information and quotas
- Job status queries
- Receives job requests from PSGC only.

Token service

- Generates JWT tokens associated with verified Slurm users.
- Ensures that only the authorized SlurmUser can issue tokens for job submission.

## Deployment Model

The Slurm Client is intended to run inside the HPC head node or login node. It is not packaged as a Kubernetes Helm chart because:

- It needs direct access to Slurm system utilities (slurmrestd).
- It interfaces directly with HPC node file systems and Slurm configuration directories.
- It runs as a systemd-managed service or directly from the CLI.

## Requirements

Before deploying the Slurm Client:

- The `slurmrestd` service must be installed and running. In order to install the `slurmrestd` service, you can visit the [Slurm documentation](https://slurm.schedmd.com/rest_quickstart.html)
- Slurm ≥ 24.11.3 must be installed (API compatibility requirement).
- A Slurm user must exist to run the HTTP server component. If Slurm is already installed, this user is typically located under `/var/lib/slurm`.
- Python ≥ 3.12 must be installed on the node.
- PSGC must be configured to point to the Slurm Client API endpoint.
- A JWT key file must be created. Refer to the official Slurm documentation for instructions on creating the file, storing it, and updating slurm.conf: [Slurm JWT Authentication](https://slurm.schedmd.com/jwt.html)

Secure communication configured between PSGC and Slurm Client via one or more methods:

- API keys
- Mutual TLS (mTLS)

Make adjustments to match your installation paths and Python virtual environment.

## Job Status Collection via Slurm Epilog

To report Slurm job completion data back to DECICE:

- Implement the epilog webhook script provided in the Slurm Client repository.
- Script responsibilities:
    - Trigger an API call to the Slurm Client on job completion.
    - Slurm Client relays the status information to the PSGC component in DECICE.
    - Update Slurm logs with success/failure of webhook transmission.
- Install the script:
    - Create an epilog directory if none exists.
    - Place the script at `/etc/slurm/epilog_slurmctld_webhook.sh`.
- Add to slurm.conf:
    - `EpilogSlurmctld=/etc/slurm/epilog_slurmctld_webhook.sh`

## Running the Client

To run and test the client, complete the following configuration steps:

- Run the client as the `slurm` user. Only the `slurm` and `root` users can generate tokens for other users in the system. Running the client with a regular user will result in permission errors.
- To run the client as the slurm user, copy the client code to the slurm user’s home directory.

1. Create a Python virtual environment:

```bash
python3.12 -m venv venv
```

3. Activate the environment and install dependencies:

```bash
$ source venv/bin/activate
$ pip install poetry
$ poetry install --no-root
```

4. Create and configure the `.env` file:

```bash
$ cd src/
$ cp .env.example .env
$ vim .env
```

5. The following is an example `.env` file configuration:

```bash
# ====================================================================
#  Slurm Client - Environment Configuration Example
#
#  To use, copy this file to '.env' (`cp .env.example .env`)
# ====================================================================

# -----------------------------------------
# Slurm Client's own setting
# -----------------------------------------
CLIENT_HOST=0.0.0.0
CLIENT_PORT=8060

# -----------------------------------------
# Slurm JWT Path Key and Algorithm
# -----------------------------------------
# (e.g., /etc/slurm/slurm.key or ./slurm.key for local dev)
SLURM_JWT_KEY_PATH="/var/spool/slurm/statesave/jwt_hs256.key"
SLURM_JWT_ALGO="HS256"

# -----------------------------------------
# Enable/Disable auto-reload
# -----------------------------------------
RELOAD=True

# -----------------------------------------
# Base URL for PSGC
# -----------------------------------------
PSGC_SERVICE_HOST=YOUR-PSGC-HOST-IP # You have to expose your PSGC from your Kubernetes cluster (i.e. IP, LoadBalancer, NodePort etc)
PSGC_SERVICE_PORT=8040 # Default port of PSGC is 8040 but if you use different port, please change it


# -----------------------------------------
# Base URLs for the Slurm REST API and SlurmDB REST API
# -----------------------------------------
SLURM_API_BASE="http://localhost:6820/slurm/v0.0.43"
SLURMDB_API_BASE="http://localhost:6820/slurmdb/v0.0.43"

# -----------------------------------------
# INTERNAL_API_KEY
# -----------------------------------------
INTERNAL_API_KEY=YOUR-API-KEY
```

After configuring the `.env` file, you can start the application with the following command:

```bash
$ python main.py
```

This will run the client as a foreground process. For production use, we recommend running the client as a `systemd` service instead.

## Deployment as Linux Services

Slurm client can be run:

- Manually from the command line (for development/testing, as explained above).
- As `systemd` services (recommended for production):
    - Ensures automatic restart on failure.
    - Runs with restricted privileges, isolated from unnecessary system directories.

Example service files are provided in the repository and can be tailored to local environment needs. The following is an example file configuration:

```bash
[Unit]
Description=FastAPI Slurm Client
After=network.target slurmctld.service

[Service]
Type=simple
User=slurm
Group=slurm
WorkingDirectory=/opt/fastapi_app
ExecStart=/opt/fastapi_venv/bin/python /opt/fastapi_app/main.py

# Security Hardening
NoNewPrivileges=yes
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/etc/slurm /var/lib/slurm /var/log/slurm /opt/fastapi_app
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
MemoryMax=300M
Environment="PYTHONUNBUFFERED=1"

Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Security Best Practices

- Use mTLS or API keys for PSGC–Slurm Client communication.
- Audit the Slurm group memberships periodically to ensure no unintended users gain token-generation rights.
- Rotate API keys and JWT signing keys periodically.
