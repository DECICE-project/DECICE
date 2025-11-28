FROM harbor.gwdg.de/decice/poetry-base:3.12-poetry2.1

RUN mkdir -p /app

ENV CM_HOST=0.0.0.0

COPY poetry.lock pyproject.toml /app/

WORKDIR /app

# Install dependencies of the project
RUN poetry install --no-root --no-interaction --no-ansi

# Copy the source code
COPY src/ /app/src/
EXPOSE 8000
CMD ["python", "src/main.py"]
