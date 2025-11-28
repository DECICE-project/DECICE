FROM python:3.12-slim-alpine

# Lock poetry version
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.1.3

# Install Deps. & Utility
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    make \
    iputils-ping \
    vim

# Minimize Image Size
RUN apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

# Install specific Poetry version via pip and disable virtualenvs
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir poetry==${POETRY_VERSION} && \
    poetry config virtualenvs.create false
