#!/bin/sh

. /venv/bhmc/bin/activate

celery -A bhmc worker --loglevel=info --concurrency 2 -E