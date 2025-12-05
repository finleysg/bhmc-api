#!/bin/sh

uv run celery -A bhmc worker --loglevel=info -E
