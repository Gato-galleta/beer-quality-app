#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
# Crea el usuario de acceso la primera vez (usa las variables DJANGO_SUPERUSER_*); si ya existe, sigue.
python manage.py createsuperuser --noinput || true
