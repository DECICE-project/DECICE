# DECICE Control Manager

[![CI Pipeline](https://img.shields.io/badge/CI-Pending-yellow)](<!-- URL to your CI pipeline -->)
[![Test Coverage](https://img.shields.io/badge/Coverage-Pending-yellow)](<!-- URL to your coverage report -->)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

The DECICE Control Manager is the central API and orchestration layer for the DECICE project. It provides a secure, robust, and extensible platform for managing users, authenticating requests, and orchestrating complex scientific workflows across distributed computing environments.

## 🏛️ Architecture Overview

This application is built using a modern, layered architecture designed for scalability, maintainability, and testability.

-   **Layered Design**: A clean separation of concerns is enforced between the API, business logic, and data access layers.
-   **Dependency Injection**: FastAPI's DI system is used extensively to manage dependencies and resources (like database sessions and HTTP clients), ensuring loose coupling and high testability.
-   **Repository Pattern**: All database interactions are encapsulated within a dedicated repository layer, abstracting the data source from the business logic.
-   **Factory Pattern**: A parser factory dynamically selects the appropriate parser for different workflow definition formats (e.g., Argo, Kubernetes Jobs, Snakemake), making the system easily extensible.
-   **Container-First**: The application is designed to be run as a containerized service, with a production-ready `Dockerfile` and a comprehensive `docker-compose` setup for local development.

## ✨ Features

-   **Secure Authentication**: JWT-based authentication with a Redis-backed session store for robust security and session management.
-   **Role-Based Access Control (RBAC)**: Differentiated permissions for standard users and administrators.
-   **Multi-Format Workflow Parsing**: Extensible support for various workflow definition files.
-   **Asynchronous from the Ground Up**: Built on FastAPI and `asyncio` for high-performance, non-blocking I/O.
-   **Comprehensive Test Suite**: High-fidelity integration tests using `testcontainers` and thorough unit tests.

## 🚀 Getting Started

### Prerequisites

-   [Git](https://git-scm.com/)
-   [Docker](https://www.docker.com/products/docker-desktop/) and [Docker Compose](https://docs.docker.com/compose/)
-   [Poetry](https://python-poetry.org/) (for managing Python dependencies locally)

### Local Development Environment

This project uses Docker Compose to provide a one-command setup for a complete, isolated development environment.

**1. Clone the Repository**
```bash
git clone <your-repository-url>
cd control-manager
```

**2. Create the Environment Configuration File**

Copy the provided example file to create your local configuration.

```bash
cp .env.example .env
```
The default values in `.env` are pre-configured to work with the `docker-compose.yml` file. No changes are needed to get started.

**3. Build and Run the Services**

This command will build the Control Manager Docker image, start the PostgreSQL and Redis containers, and launch the application with live reloading.

```bash
docker-compose up --build
```

The API will be running and accessible at [http://localhost:8000/docs](http://localhost:8000/docs).

**Key Features of this Setup:**
-   **Live Reloading:** Any changes you make to the source code in the `src/` directory will cause the application to automatically restart inside the container.
-   **Persistent Data:** Your database and Redis data are stored in Docker volumes and will persist between `docker-compose down` and `docker-compose up`.

**4. Stopping the Environment**

To stop and remove the containers, press `Ctrl+C` in the terminal where Compose is running, then execute:
```bash
docker-compose down
```

## 🧪 Running the Test Suite

The project includes a comprehensive test suite that should be run before committing any changes.

**1. Run All Tests**

This command will execute both unit and integration tests. The integration tests will automatically spin up their own dedicated PostgreSQL and Redis containers using `testcontainers`.

```bash
pytest
```

**2. Run Tests with Coverage Report**

To run the tests and generate a report on code coverage, use the `coverage` tool.

```bash
# Run the tests under coverage
coverage run -m pytest

# Display the coverage report in the terminal
coverage report -m
```

## ⚙️ Configuration

The application is configured via environment variables, which are loaded by `pydantic-settings` from a `.env` file. To get started, copy the template: `cp .env.example .env`.

| Variable | Description | Default (in `.env.example`) |
| :--- | :--- | :--- |
| **Application** | | |
| `APP_ENV` | The application environment ('development' or 'production'). | `development` |
| **Database** | | |
| `POSTGRES_USER` | The username for the PostgreSQL database. | `myuser` |
| `POSTGRES_PASSWORD` | The password for the PostgreSQL user. | `mypassword` |
| `POSTGRES_DB` | The name of the database to use. | `userdb` |
| `DATABASE_URL` | The full SQLAlchemy connection string. Uses service name **`postgres`**. | `postgresql+psycopg://...` |
| **Redis** | | |
| `REDIS_URL` | The connection URL for the Redis instance. Uses service name **`redis`**. | `redis://redis:6379/0` |
| **Security** | | |
| `SESSION_EXPIRE_SECONDS` | The duration (in seconds) for a user session in Redis. | `3600` |
| `JWT_SECRET_KEY` | A 64-character hex string (32 bytes) for signing JWTs. **Must be provided.** | A development key is in the example. |
| `JWT_ALGORITHM` | The algorithm to use for JWT signing. | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | The lifespan (in minutes) of a JWT access token. | `60` |


## 📂 Project Structure
```
├── .env                  # Local environment configuration (gitignored)
├── .env.example          # Example environment file
├── docker-compose.yml    # Docker Compose orchestration for local development
├── Dockerfile            # Multi-stage Dockerfile for production builds
├── poetry.lock           # Poetry lock file for reproducible dependencies
├── pyproject.toml        # Project definition and dependencies for Poetry
├── src/
│   ├── api/              # FastAPI application, routers, and lifespan manager
│   ├── auth/             # Authentication, authorization, and security logic
│   ├── clients/          # Clients for communicating with external services
│   ├── config.py         # Pydantic settings management
│   ├── core/             # Core application components (e.g., dependencies)
│   ├── db/               # Database models and session management
│   ├── domain/           # Pydantic schemas for data contracts
│   ├── main.py           # Application entrypoint for production
│   ├── parser/           # Workflow definition file parsers (Factory Pattern)
│   ├── repositories/     # Data access layer (Repository Pattern)
│   ├── services/         # Business logic and service orchestration
│   └── session/          # Redis session management
└── tests/
    ├── conftest.py       # Pytest fixtures and test configuration
    ├── integration/      # Integration tests (full app stack)
    └── unit/             # Unit tests (isolated components)
```

### 💅 Code Quality and Linting

We use `ruff` to enforce a consistent code style and catch common errors.

**1. Check and Format Code**

The `lint` command will automatically format your code and report any style violations or potential bugs.

```bash
make lint
```

### 📚 Building Documentation

The project documentation can be generated locally. This is useful for previewing changes before they are deployed.

**1. Install Documentation Dependencies**

This command uses Poetry to install the necessary tools (like Sphinx) for building the docs. You only need to run this once.

```bash
make install-docs
```

**2. Build the HTML Docs**

This command will generate the documentation as a static HTML website.

```bash
make docs
```
The output will be located in the `docs/_build/html` directory. You can open the `index.html` file in your browser to view the documentation.


## 🤝 Contributing

Contributions are welcome! Please open an issue to discuss a new feature or bug. Pull requests should be linked to an existing issue and must pass all tests and linting checks.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
