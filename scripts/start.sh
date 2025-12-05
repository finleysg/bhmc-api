#!/bin/sh

until uv run python manage.py migrate; do
  echo "Waiting for the database to be ready..."
  sleep 2
done

uv run python -Xfrozen_modules=off manage.py runserver 0.0.0.0:8000
