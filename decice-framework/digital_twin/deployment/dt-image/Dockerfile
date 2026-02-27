FROM harbor.gwdg.de/decice/poetry-base:3.12-poetry2.1

RUN mkdir -p /app

ENV DT_HOST=0.0.0.0

COPY configs/ /app/configs/

COPY scripts/ /app/scripts/

COPY examples/ /app/examples/

COPY pyproject.toml README.md /app/

COPY src/ /app/src/

WORKDIR /app

RUN poetry install --no-cache --no-interaction --no-root

EXPOSE 8010


CMD ["python", "src/digital_twin/main.py"]
