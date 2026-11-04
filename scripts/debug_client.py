import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beer_quality.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from quality.agents.parameters import EXAMPLE_LOT

# El endpoint requiere sesion: usa el primer usuario activo de la base de datos
user = get_user_model().objects.filter(is_active=True).first()
if user is None:
    sys.exit('No hay usuarios. Crea uno con: python manage.py createsuperuser')

client = Client()
client.force_login(user)

resp = client.post('/quality/predict/', data=json.dumps(EXAMPLE_LOT), content_type='application/json')
print('status', resp.status_code)
print('content', resp.content.decode())
