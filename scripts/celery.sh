#!/bin/sh

. /venv/bhmc/bin/activate

celery -A bhmc worker --loglevel=info -E
