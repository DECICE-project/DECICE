FROM harbor.gwdg.de/decice/poetry-base:3.12-poetry2.1

RUN mkdir -p /app

ENV PROMQL_WRAPPER_HOST=0.0.0.0 \
    PYTHONPATH="/usr/local/lib/python3.12/site-packages"

COPY pyproject.toml poetry.lock README.md /app/

COPY src/ /app/src/

WORKDIR /app

RUN poetry install --no-cache --no-interaction --no-root
# Run
CMD ["python", "src/main.py"]
