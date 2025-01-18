#!/bin/sh

. /venv/bhmc/bin/activate

until python manage.py migrate
do
  echo "Waiting for the database to be ready..."
  sleep 2
done

python manage.py runserver 0.0.0.0:8000