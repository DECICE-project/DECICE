FROM harbor.gwdg.de/decice/poetry-base:3.12-poetry2.1

RUN mkdir -p /app

ENV PYTHONUNBUFFERED=1 \
    PSGC_HOST=0.0.0.0

COPY poetry.lock pyproject.toml /app/

WORKDIR /app

RUN poetry install --no-cache --no-interaction --no-root

COPY src/ /app/src/

EXPOSE 8040

CMD ["python", "src/main.py"]
