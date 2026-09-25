from django.core.exceptions import ValidationError
from django.db import transaction

from directories.models import AuditEntry
from directories.services import save_record

from .models import EquipmentTechnologyCard, TechnologyCard


@transaction.atomic
def save_technology_card(form, operation_formset, material_formset, actor):
    card = save_record(form, actor)
    operation_formset.instance = card
    material_formset.instance = card
    operation_formset.save()
    material_formset.save()
    return card


@transaction.atomic
def save_equipment_assignments(equipment, cards, actor):
    current = set(
        EquipmentTechnologyCard.objects.filter(equipment=equipment).values_list('technology_card_id', flat=True)
    )
    requested = {card.pk for card in cards}
    invalid = [card for card in cards if card.equipment_model_id != equipment.equipment_model_id]
    if invalid:
        raise ValidationError('Одна или несколько карт относятся к другой модели техники.')

    EquipmentTechnologyCard.objects.filter(
        equipment=equipment,
        technology_card_id__in=current - requested,
    ).delete()
    for card in cards:
        EquipmentTechnologyCard.objects.get_or_create(
            equipment=equipment,
            technology_card=card,
            defaults={'assigned_by': actor},
        )

    if current != requested:
        AuditEntry.objects.create(
            actor=actor,
            model_name=equipment._meta.model_name,
            object_id=equipment.pk,
            object_label=str(equipment)[:400],
            action='update',
            before={'technology_card_ids': sorted(current)},
            after={'technology_card_ids': sorted(requested)},
        )


def grouped_operations(card):
    groups = []
    current_section = None
    current_operations = None
    for operation in card.operations.all():
        section = operation.section or 'Без раздела'
        if section != current_section:
            current_section = section
            current_operations = []
            groups.append((section, current_operations))
        current_operations.append(operation)
    return groups
