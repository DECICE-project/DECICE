# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl libgomp1 tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/data /app/artifacts

COPY requirements.txt /app/requirements.txt

# Faster rebuilds if you enable BuildKit (DOCKER_BUILDKIT=1):
# docker buildx build ...
# This cache mount keeps wheel downloads between builds.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r /app/requirements.txt

COPY app/ /app/

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Use tini so the app handles signals/children well in Kubernetes
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "k8s_collect.py"]
