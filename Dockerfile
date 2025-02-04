FROM ubuntu:24.04 AS base

FROM base AS builder

RUN apt update && apt install --no-install-recommends -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  build-essential \
  default-libmysqlclient-dev \
  pkg-config

FROM builder AS stage

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN mkdir /venv \
  && python3 -m venv /venv/bhmc

RUN mkdir /scripts
COPY ./scripts /scripts

RUN chmod +x /scripts/start.sh
RUN chmod +x /scripts/celery.sh
RUN chmod +x /scripts/celery-beat.sh

RUN mkdir /app
WORKDIR /app

COPY ./requirements.txt .
RUN /venv/bhmc/bin/pip install --no-cache-dir --upgrade pip \
  && /venv/bhmc/bin/pip install --no-cache-dir -r /app/requirements.txt
