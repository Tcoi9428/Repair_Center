from django.db import migrations


def assign_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Role = apps.get_model('accounts', 'Role')
    models = {
        'maintenancetype': 'вид технического обслуживания',
        'material': 'материал технологической карты',
        'technologycard': 'технологическая карта',
    }
    permissions = {}
    for model, label in models.items():
        content_type, _ = ContentType.objects.get_or_create(app_label='maintenance', model=model)
        for action in ('view', 'add', 'change'):
            permission, _ = Permission.objects.get_or_create(
                content_type=content_type,
                codename=f'{action}_{model}',
                defaults={'name': f'Can {action} {label}'},
            )
            permissions[(model, action)] = permission
    for role in Role.objects.select_related('group'):
        for model in models:
            role.group.permissions.add(permissions[(model, 'view')])
            if role.code in ('SYS_ADMIN', 'NSI'):
                role.group.permissions.add(
                    permissions[(model, 'add')],
                    permissions[(model, 'change')],
                )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_alter_accessevent_action'),
        ('maintenance', '0001_initial'),
    ]

    operations = [migrations.RunPython(assign_permissions, migrations.RunPython.noop)]
