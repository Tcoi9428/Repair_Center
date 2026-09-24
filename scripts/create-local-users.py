"""One-time local development accounts. Credentials never go to stdout."""
import os
import sys
import secrets
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from accounts.models import Role
from django.db import transaction

if not settings.DEBUG or settings.DATABASES['default']['HOST'] not in ('127.0.0.1', 'localhost'):
    raise SystemExit('Only local DEBUG installations are supported.')
User = get_user_model()
if User.objects.filter(username__in=['admin', 'nsi']).exists():
    raise SystemExit('Accounts already exist; passwords were not changed.')
credentials = {name: secrets.token_urlsafe(18) for name in ('admin', 'nsi')}
with transaction.atomic():
    admin = User.objects.create_superuser('admin', password=credentials['admin'])
    admin.groups.add(Role.objects.get(code='SYS_ADMIN').group)
    user = User.objects.create_user('nsi', password=credentials['nsi'], first_name='Специалист', last_name='НСИ')
    user.groups.add(Group.objects.get(name='Специалист НСИ'))
    local = root / '.local'
    local.mkdir(exist_ok=True)
    (local / 'access.json').write_text(json.dumps(credentials), encoding='utf-8')
    (local / 'access.txt').write_text(
        'Ремонтный Центр — локальная разработка\nhttp://127.0.0.1:8000/\n\n'
        f"Специалист НСИ\nЛогин: nsi\nПароль: {credentials['nsi']}\n\n"
        f"Администратор: http://127.0.0.1:8000/admin/\nЛогин: admin\nПароль: {credentials['admin']}\n\n"
        'Файл содержит пароли. Не включать в Git и общие архивы проекта.\n', encoding='utf-8')
print('Local accounts created. Credentials: .local/access.txt')
