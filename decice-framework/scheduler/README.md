# AI Scheduler

[![CI Pipeline](https://img.shields.io/badge/CI-Pending-yellow)](<!-- URL to your CI pipeline -->)
[![Test Coverage](https://img.shields.io/badge/Coverage-Pending-yellow)](<!-- URL to your coverage report -->)

The AI Scheduler is the intelligent decision-making core of the DECICE scheduling system. It is a specialized microservice that receives scheduling requests (jobs and node states) and uses a Reinforcement Learning (RL) model to predict the most optimal scheduling strategy for the given situation.

## Core Responsibility & Architecture

This service implements a complete machine learning pipeline:

1.  **Data Transformation:** It ingests raw job and node data and transforms it into a standardized format using an internal `DataTransformer`.
2.  **Pre-filtering:** A `FuzzyStorageResourcesAccessGate` performs an initial, fuzzy-logic-based assessment to determine which nodes are suitable for each job.
3.  **AI Prediction:** A Proximal Policy Optimization (PPO) model, managed by the `AIScheduler` class, analyzes the overall state and **predicts** which scheduling algorithm (e.g., "MCT", "ILP", "Shortest Job First") is best suited for the current scenario.
4.  **Strategy Execution:** The **Kairos** engine, using a **Strategy Pattern**, dynamically executes the algorithm chosen by the AI.
5.  **Experience Collection:** The results of the scheduling decision (runtime, throughput) are collected as "experience" in a replay buffer, which can be used for offline training to continuously improve the AI model.

## Structure
* `/src`
    * `/core`: source code
    * `/data`: .pkl files for buffer, scenario data
    * `/models`: .joblib scalers, .h5 model files
    * `/scripts`: scripts for evaluation, training data generation, training models
    * `/strategies`: scheduling strategies
* `api.py`: microservice http setup
* `main.py`: entry point, application setup
* `strategy_loader.py`: factory for dynamically loading strategies

## 🚀 Getting Started

This service can be run as part of the unified, multi-service environment or in a standalone mode for focused development.

### Running with the Full System (Recommended)

Please see the main `README.md` in the project's root directory for instructions on how to run the entire DECICE system with the master `docker-compose.yml`.

### Standalone Development

For working exclusively on the AI Scheduler, you can use its own local Docker Compose environment.

**1. Configure Environment**
Copy the environment template. The defaults are pre-configured to work with the Docker setup.
```bash
cp .env.example .env
```

**2. Launch the Service**
This command will build the Docker image and start the service with live reloading.
```bash
docker-compose up --build
```
The API will be available at [http://localhost:8030/docs](http://localhost:8030/docs). Any changes to the source code will trigger an automatic restart.

## 🧪 Running Tests

The service includes a suite of unit tests for its core components and integration tests for the API layer.

```bash
# Run all tests
poetry run pytest

# Run with a detailed coverage report
poetry run coverage run -m pytest
poetry run coverage report -m
```

## 🤖 Offline ML Operations

This project includes scripts for managing the ML model's lifecycle (data generation, training, and evaluation).

**1. Generate Synthetic Scenarios**
Creates JSON files with randomized job and node data for training and evaluation.
```bash
poetry run python src/scripts/generate_synthetic_data.py --num_files 50
```

**2. Populate the Replay Buffer**
Runs all scheduling strategies against the synthetic scenarios and saves the outcomes (state, action, reward) to a replay buffer file. This is the training data for the RL agent.
```bash
poetry run python src/scripts/populate_replay_buffer.py
```

**3. Train the AI Model**
Trains the PPO (Actor-Critic) models using the data from the replay buffer.
```bash
poetry run python src/scripts/train_ai_scheduler.py
```

**4. Evaluate the Trained Model**
Runs the trained AI model against a set of test scenarios and provides a performance summary.
```bash
poetry run python src/scripts/evaluate_ai_scheduler.py
```

*Note: check `README.md` in `/scripts` for setting up project models*

## 📄 API Contract

The full OpenAPI specification is available at the `/docs` route when the service is running.

-   **`POST /schedule`**: The primary endpoint. Receives a `ScheduleRequest` and returns a `ScheduleResponse` with the final job placements.
-   **`GET /health`**: A health check endpoint that verifies the successful initialization of all core components.

## ⚙️ Configuration

The service is configured via environment variables, documented in `.env.example`.

| Variable | Description | Default (in `.env.example`) |
| :--- | :--- | :--- |
| `ENVIRONMENT` | The runtime environment. | `local` |
| `LOG_LEVEL` | The application's logging verbosity. | `INFO` |
| `API_HOST` | The host on which the service will run. | `0.0.0.0` |
| `API_PORT` | The port on which the service will listen. | `8030` |

*Note: All ML hyperparameters and file paths are also configurable via environment variables but have sensible defaults set in `src/core/config.py`.*
