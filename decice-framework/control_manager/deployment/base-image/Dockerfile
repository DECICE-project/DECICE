FROM docker.gitlab-ce.gwdg.de/utilize/repositories:python-3.12-slim-bullseye as python


FROM python as decice-python-base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

#ARG APT_REPO_CREDENTIALS
#ARG PIP_REPO_CREDENTIALS

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    apt-transport-https \
    gcc \
    libc-dev \
    gettext \
    libpq-dev \
    postgresql-client \
    python3-dev \
    gdal-bin \
    libgdal-dev \
    supervisor \
    procps curl \
    wget net-tools \
    bmon \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip --timeout=60 install -U pip \
    && pip --timeout=60 install --no-cache-dir -r requirements.txt