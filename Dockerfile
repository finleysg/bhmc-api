FROM ubuntu:24.04

# Install uv and system dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt update && apt install --no-install-recommends -y \
  python3 \
  python3-dev \
  build-essential \
  default-libmysqlclient-dev \
  pkg-config

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN mkdir /scripts
COPY ./scripts /scripts
RUN chmod +x /scripts/*.sh

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Ensure .venv is cleaned up before syncing dependencies
RUN rm -rf .venv && uv sync --frozen --no-dev

# Copy application code
COPY . .
