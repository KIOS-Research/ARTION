#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python manage.py migrate
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

# custom manage commands for user creation and db initialization
python manage.py dump_super_user
python manage.py init_db

exec "$@"