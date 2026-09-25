import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from directories.models import AuditEntry, Equipment, EquipmentModel
from maintenance.importers import build_markdown_summary, parse_workbook
from maintenance.models import (
    EquipmentTechnologyCard,
    MaintenanceType,
    Material,
    TechnologyCard,
    TechnologyCardMaterial,
    TechnologyCardOperation,
)


class Command(BaseCommand):
    help = 'Импортирует технологические карты из чек-листов Excel.'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--model', default='ПДМ 10 ШААЗ', help='Наименование модели техники в системе.')
        parser.add_argument('--revision', type=int, help='Версия карт. По умолчанию определяется из имени файла.')
        parser.add_argument('--replace', action='store_true', help='Заменить операции и материалы существующих карт этой версии.')
        parser.add_argument('--assign-existing', action='store_true', help='Назначить карты существующим единицам выбранной модели.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--summary', help='Путь для сохранения Markdown-сводки извлечения.')

    @transaction.atomic
    def handle(self, *args, **options):
        source = Path(options['path'])
        if not source.exists():
            raise CommandError(f'Файл не найден: {source}')
        try:
            cards = parse_workbook(source)
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        if not cards:
            raise CommandError('В книге нет видимых листов с технологическими картами.')

        revision = options['revision']
        if revision is None:
            match = re.search(r'[Vv](\d+)', source.stem)
            revision = int(match.group(1)) if match else 1
        if revision < 1:
            raise CommandError('Версия должна быть положительным числом.')

        try:
            equipment_model = EquipmentModel.objects.get(name=options['model'])
        except EquipmentModel.DoesNotExist as exc:
            raise CommandError(f'Модель техники «{options["model"]}» не найдена.') from exc

        created_count = updated_count = skipped_count = 0
        for parsed in cards:
            maintenance_type, _ = MaintenanceType.objects.get_or_create(
                code=f'TO-{parsed.interval_hours}',
                defaults={
                    'name': f'ТО-{parsed.interval_hours}',
                    'interval_hours': parsed.interval_hours,
                    'description': f'Регламентное техническое обслуживание через {parsed.interval_hours} моточасов.',
                },
            )
            card = TechnologyCard.objects.filter(
                equipment_model=equipment_model,
                maintenance_type=maintenance_type,
                revision=revision,
            ).first()
            if card and not options['replace']:
                skipped_count += 1
                self.stdout.write(f'Пропущено: {card} уже существует. Для замены используйте --replace.')
                continue
            created = card is None
            if created:
                card = TechnologyCard(
                    equipment_model=equipment_model,
                    maintenance_type=maintenance_type,
                    revision=revision,
                )
            card.name = f'{maintenance_type.name} · {equipment_model.name}'
            card.status = TechnologyCard.Status.DRAFT
            card.source_name = source.name
            card.notes = f'Импортировано с листа «{parsed.sheet_name}». Требуется проверка специалистом НСИ.'
            card.full_clean()
            card.save()
            if not created:
                card.operations.all().delete()
                card.required_materials.all().delete()
                updated_count += 1
            else:
                created_count += 1

            TechnologyCardOperation.objects.bulk_create(
                [
                    TechnologyCardOperation(
                        technology_card=card,
                        sequence=item.sequence,
                        section=item.section,
                        operation_number=item.operation_number,
                        description=item.description,
                        standard_minutes=item.standard_minutes,
                        is_required=True,
                    )
                    for item in parsed.operations
                ]
            )
            material_lines = []
            for item in parsed.materials:
                material = None
                if item.nomenclature_number:
                    material = Material.objects.filter(
                        nomenclature_number__iexact=item.nomenclature_number
                    ).first()
                if material is None and not item.nomenclature_number:
                    material = Material.objects.filter(
                        nomenclature_number='', name__iexact=item.name, default_unit=item.unit
                    ).first()
                if material is None:
                    material = Material.objects.create(
                        nomenclature_number=item.nomenclature_number,
                        name=item.name,
                        default_unit=item.unit,
                    )
                material_lines.append(
                    TechnologyCardMaterial(
                        technology_card=card,
                        material=material,
                        sequence=item.sequence,
                        kind=item.kind,
                        quantity=item.quantity,
                        unit=item.unit,
                        notes=item.notes,
                    )
                )
            TechnologyCardMaterial.objects.bulk_create(material_lines)
            AuditEntry.objects.create(
                actor=None,
                model_name='technologycard',
                object_id=card.pk,
                object_label=str(card)[:400],
                action='create' if created else 'update',
                before={},
                after={
                    'source': source.name,
                    'sheet': parsed.sheet_name,
                    'operations': len(parsed.operations),
                    'materials': len(parsed.materials),
                },
            )
            if options['assign_existing']:
                for equipment in Equipment.objects.filter(equipment_model=equipment_model):
                    link = EquipmentTechnologyCard(equipment=equipment, technology_card=card)
                    try:
                        link.full_clean()
                    except ValidationError as exc:
                        raise CommandError(str(exc)) from exc
                    EquipmentTechnologyCard.objects.get_or_create(equipment=equipment, technology_card=card)

        if options['summary']:
            summary_path = Path(options['summary'])
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(build_markdown_summary(source, cards), encoding='utf-8')

        if options['dry_run']:
            transaction.set_rollback(True)
        result = f'Создано: {created_count}; обновлено: {updated_count}; пропущено: {skipped_count}.'
        if options['dry_run']:
            result += ' Проверочный запуск: изменения не сохранены.'
        self.stdout.write(self.style.SUCCESS(result))
