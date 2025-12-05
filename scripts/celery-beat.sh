#!/bin/sh

uv run celery -A bhmc beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
