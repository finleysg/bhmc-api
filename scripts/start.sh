#!/bin/sh

. /venv/bhmc/bin/activate

until python manage.py migrate
do
  echo "Waiting for the database to be ready..."
  sleep 2
done

# https://bugs.python.org/issue1666807#msg416932
python -Xfrozen_modules=off manage.py runserver 0.0.0.0:8000