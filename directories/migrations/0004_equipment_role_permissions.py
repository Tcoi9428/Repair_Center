from django.db import migrations


def add_equipment_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    content_type, _ = ContentType.objects.get_or_create(app_label='directories', model='equipment')
    permissions = {}
    for action, name in (
        ('view', 'Can view Оборудование'),
        ('add', 'Can add Оборудование'),
        ('change', 'Can change Оборудование'),
    ):
        permissions[action], _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=f'{action}_equipment',
            defaults={'name': name},
        )
    for role in Role.objects.select_related('group').all():
        role.group.permissions.add(permissions['view'])
        if role.code in ('SYS_ADMIN', 'NSI'):
            role.group.permissions.add(permissions['add'], permissions['change'])


class Migration(migrations.Migration):
    dependencies = [
        ('directories', '0003_equipment_equipmentdocument'),
        ('accounts', '0003_alter_accessevent_action'),
    ]
    operations = [migrations.RunPython(add_equipment_permissions, migrations.RunPython.noop)]
