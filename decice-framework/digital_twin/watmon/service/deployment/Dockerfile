FROM harbor.gwdg.de/decice/poetry-base:3.12-poetry2.1

WORKDIR /watmon_service

# Copy poetry config file and install dependencies
COPY pyproject.toml poetry.lock ./
# Set Poetry to create a virtual environment
RUN poetry config virtualenvs.create true \
    && poetry install  --no-interaction --no-root

COPY . .

# Install the project after copying the source code
RUN poetry install --no-interaction

CMD ["poetry", "run", "python", "watmon_service/api.py"]
