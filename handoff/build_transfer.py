from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[1]
session = Path(r'C:\Users\i.petrikin\.codex\sessions\2026\09\03\rollout-2026-09-03T14-35-46-01a0669f-d81e-7843-ac97-0e93f35f3827.jsonl')
original = Path(r'C:\Users\i.petrikin\Desktop\Work\10.Проект внедрения 1С-ТОиР\Пакет документов для отправки на ШААЗ\ТЗ на внедрение системы управления ТОиР.pdf')
source_dir = root / 'source-documents'
source_dir.mkdir(exist_ok=True)
source_copy = source_dir / 'maintenance-requirements-original.pdf'
shutil.copy2(original, source_copy)

def portable(text):
    text = text.replace(str(original), 'source-documents/maintenance-requirements-original.pdf')
    text = text.replace(original.as_posix(), 'source-documents/maintenance-requirements-original.pdf')
    text = text.replace(str(root) + '\\', '').replace(root.as_posix() + '/', '')
    text = text.replace(str(root), '[корень проекта RepairCenter]')
    text = re.sub(r':codex-file-citation\{path="source-documents/maintenance-requirements-original.pdf" purpose="source"\}', '[Исходное ТЗ](source-documents/maintenance-requirements-original.pdf)', text)
    return text

messages = []
for line in session.read_text(encoding='utf-8').splitlines():
    item = json.loads(line)
    p = item.get('payload', {})
    if item.get('type') != 'response_item' or p.get('type') != 'message':
        continue
    role = p.get('role')
    if role not in ('user', 'assistant') or p.get('channel') in ('analysis', 'summary'):
        continue
    content = '\n'.join(c.get('text', '') for c in p.get('content', []) if c.get('type') in ('input_text', 'output_text', 'text'))
    if not content.strip():
        continue
    content = re.sub(r'<recommended_plugins>[\s\S]*?</recommended_plugins>', '', content)
    content = re.sub(r'<environment_context>[\s\S]*?</environment_context>', '', content).strip()
    if not content:
        continue
    label = 'Пользователь' if role == 'user' else 'Ассистент'
    messages.append(f'## {len(messages)+1}. {label}\n\n{portable(content)}\n')
    if role == 'user' and 'файл со всем контекстом данного проекта и чата' in content:
        break
assert len(messages) >= 25, 'Unexpectedly incomplete message history'
history = '# Текст переписки по проекту RepairCenter\n\n' \
    'Экспорт видимых текстовых сообщений пользователя и ассистента по текущий запрос передачи контекста от 08.09.2026 включительно. Сохранены ответы и промежуточные сообщения. Исключены служебные инструкции среды, вызовы инструментов и их вывод, внутренние рассуждения. Генерации изображений доступны отдельными файлами. Ссылки на файлы проекта адаптированы к новой папке; внешние исторические пути могут требовать обращения к карте материалов. Повтор запроса логотипа отражает прерванный и повторенный запрос пользователя.\n\n' \
    + '\n'.join(messages)
(root / 'CHAT_HISTORY.md').write_text(history, encoding='utf-8')

overview = (root / 'handoff/context-overview.md').read_text(encoding='utf-8')
appendices = [
    ('А. Полное техническое предложение от 03.09.2026', 'analysis/implementation-proposal.md'),
    ('Б. Принципы интерфейса и выбранная палитра', 'design/concepts/design-notes.md'),
    ('В. Статус выбора логотипа', 'design/logo/README.md'),
    ('Г. Правила применения готового логотипа', 'static/branding/README.md'),
    ('Д. Текст переписки', 'CHAT_HISTORY.md'),
]
sections = [overview]
for title, filename in appendices:
    body = portable((root / filename).read_text(encoding='utf-8'))
    sections.append(f'\n\n---\n\n# Приложение {title}\n\nИсточник: `{filename}`. Вложения и относительные ссылки в исходном документе относятся к его расположению; для переходов используйте карту материалов в разделе 11.\n\n{body}')
(root / 'PROJECT_CONTEXT.md').write_text('\n'.join(sections), encoding='utf-8')

files = [root / 'PROJECT_CONTEXT.md', root / 'CHAT_HISTORY.md']
for folder in ['analysis', 'design', 'static', 'source-documents']:
    files.extend(sorted((root / folder).rglob('*')))
files = sorted({p for p in files if p.is_file()})
manifest = {
    'project': 'RepairCenter', 'snapshot_date': '2026-09-08',
    'entrypoint': 'PROJECT_CONTEXT.md', 'source_thread_id': '01a0669f-d81e-7843-ac97-0e93f35f3827',
    'git': {'branch': 'master', 'commits': 0, 'remotes': []},
    'files': [{'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size,
               'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
}
manifest_path = root / 'TRANSFER_MANIFEST.json'
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
archive_path = root / 'RepairCenter-transfer-2026-09-08.zip'
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files + [manifest_path]:
        z.write(p, 'RepairCenter/' + p.relative_to(root).as_posix())

with zipfile.ZipFile(archive_path) as z:
    assert z.testzip() is None
    for f in manifest['files']:
        data = z.read('RepairCenter/' + f['path'])
        assert len(data) == f['bytes']
        assert hashlib.sha256(data).hexdigest() == f['sha256']
    assert not any('/.git/' in n or '/tmp/' in n for n in z.namelist())
assert hashlib.sha256(original.read_bytes()).digest() == hashlib.sha256(source_copy.read_bytes()).digest()
context = (root / 'PROJECT_CONTEXT.md').read_text(encoding='utf-8')
assert '\ufffd' not in context
assert 'Мне нравится айдентика № 2' in context
assert '#006cb5' in context and 'PostgreSQL' in context
print(json.dumps({'context_file': str(root / 'PROJECT_CONTEXT.md'), 'context_bytes': (root / 'PROJECT_CONTEXT.md').stat().st_size,
                  'messages': len(messages), 'archive': str(archive_path), 'archive_bytes': archive_path.stat().st_size,
                  'files_in_archive': len(files)+1, 'verification': 'ZIP CRC and SHA-256 for every content file passed; PDF copy matches original'}, ensure_ascii=False, indent=2))
