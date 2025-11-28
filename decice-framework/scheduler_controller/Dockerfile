# Stage 1: Build the virtual environment
FROM python:3.12-slim-bookworm AS builder

RUN pip install poetry

ENV POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root


# Stage 2: Create final production image 
FROM python:3.12-slim-bookworm AS final

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /app/.venv ./.venv

COPY ./src ./src

RUN chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/src

CMD ["python", "main.py"]
