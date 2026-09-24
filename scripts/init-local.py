"""One-time local PostgreSQL setup; no machine-wide service or open interfaces."""
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / '.local'
BIN = LOCAL / 'postgresql' / 'pgsql' / 'bin'
DATA = LOCAL / 'pgdata'
ENV = ROOT / '.env'
if not BIN.is_dir():
    raise SystemExit('Распакуйте PostgreSQL в .local/postgresql (каталог pgsql/bin).')
if DATA.exists() or ENV.exists():
    raise SystemExit('Локальная база или .env уже существуют. Используйте scripts/start-local.ps1.')
password = secrets.token_urlsafe(32)
password_file = LOCAL / 'init-password.txt'
password_file.write_text(password, encoding='ascii')
try:
    subprocess.run([str(BIN / 'initdb.exe'), '-D', str(DATA), '-U', 'repaircenter',
                    '-A', 'scram-sha-256', '--pwfile', str(password_file), '-E', 'UTF8',
                    '--locale-provider=icu', '--icu-locale=ru-RU', '--locale=C'], check=True)
finally:
    password_file.unlink(missing_ok=True)
with (DATA / 'postgresql.conf').open('a', encoding='utf-8') as file:
    file.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
subprocess.run([str(BIN / 'pg_ctl.exe'), '-D', str(DATA), '-l', str(LOCAL / 'postgres.log'), 'start', '-w'], check=True)
env = os.environ.copy()
env['PGPASSWORD'] = password
subprocess.run([str(BIN / 'createdb.exe'), '-h', '127.0.0.1', '-p', '55432', '-U', 'repaircenter', 'repaircenter'], env=env, check=True)
ENV.write_text(f'DJANGO_SECRET_KEY={secrets.token_urlsafe(48)}\nDJANGO_DEBUG=True\nDJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,testserver\nPGDATABASE=repaircenter\nPGUSER=repaircenter\nPGPASSWORD={password}\nPGHOST=127.0.0.1\nPGPORT=55432\n', encoding='utf-8')
print('Локальная PostgreSQL готова: 127.0.0.1:55432 / repaircenter. Секреты сохранены в .env.')

