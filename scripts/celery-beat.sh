#!/bin/sh

. /venv/bhmc/bin/activate

celery -A bhmc beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
