from django.db import migrations


def use_numeric_identifiers(apps, schema_editor):
    Equipment = apps.get_model('directories', 'Equipment')
    for item in Equipment.objects.select_related('operating_company').all():
        item.equipment_identifier = (
            f'{item.operating_company.code}{item.equipment_type_id}'
            f'{item.equipment_model_id}{item.factory_number}'
        )
        item.save(update_fields=['equipment_identifier'])


def restore_previous_identifiers(apps, schema_editor):
    Equipment = apps.get_model('directories', 'Equipment')
    for item in Equipment.objects.select_related('operating_company', 'equipment_type').all():
        item.equipment_identifier = (
            f'{item.operating_company.code}-{item.equipment_type.short_name}-'
            f'{item.equipment_model_id:04d}-{item.factory_number}'
        )
        item.save(update_fields=['equipment_identifier'])


class Migration(migrations.Migration):
    dependencies = [('directories', '0004_equipment_role_permissions')]
    operations = [migrations.RunPython(use_numeric_identifiers, restore_previous_identifiers)]
