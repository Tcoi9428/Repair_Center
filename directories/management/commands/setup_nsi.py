from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from directories.catalog import CATALOGS
from directories.models import EquipmentType, EquipmentModel, EquipmentAttribute, WarrantyAttribute, EquipmentStatus
from directories.services import record_change

ROLE_NAME = 'Специалист НСИ'

class Command(BaseCommand):
    help = 'Создает роль НСИ; --seed добавляет исходные значения; --username назначает роль существующему пользователю.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', action='store_true')
        parser.add_argument('--username')

    @transaction.atomic
    def handle(self, *args, **options):
        role, _ = Group.objects.get_or_create(name=ROLE_NAME)
        for catalog in CATALOGS:
            for action in ('view', 'add', 'change'):
                permission = Permission.objects.get(
                    content_type__app_label=catalog.model._meta.app_label,
                    codename=f'{action}_{catalog.model._meta.model_name}',
                )
                role.permissions.add(permission)
        for action in ('view', 'add', 'change'):
            role.permissions.add(
                Permission.objects.get(
                    content_type__app_label='maintenance',
                    codename=f'{action}_technologycard',
                )
            )
        role.permissions.add(Permission.objects.get(content_type__app_label='directories', codename='view_auditentry'))
        if options['username']:
            from django.contrib.auth import get_user_model
            try:
                user = get_user_model().objects.get(username=options['username'])
            except get_user_model().DoesNotExist as exc:
                raise CommandError('Пользователь не найден.') from exc
            user.groups.add(role)
        if options['seed']:
            def seed(model, **fields):
                obj, created = model.objects.get_or_create(name=fields.pop('name'), defaults=fields)
                if created:
                    record_change(obj, None, {}, 'create')
                return obj
            pdm = seed(EquipmentType, name='Погрузочно-доставочная машина', short_name='ПДМ', purpose='Погрузка и доставка горной массы в подземных выработках.')
            seed(EquipmentType, name='Шахтный автосамосвал', short_name='ШАС', purpose='Транспортирование горной массы в подземных выработках.')
            seed(EquipmentType, name='Самоходная буровая установка', short_name='СБУ', purpose='Бурение шпуров и скважин при ведении горных работ.')
            seed(EquipmentType, name='Шахтная вспомогательная техника', short_name='ШВТ', purpose='Выполнение вспомогательных и обеспечивающих работ в шахте.')
            for name, capacity in [('ПДМ 10 ШААЗ', 10), ('ПДМ 14 ШААЗ', 14), ('ПДМ 17 ШААЗ', 17), ('ПДМ 14 Исеть', 14)]:
                obj, created = EquipmentModel.objects.get_or_create(equipment_type=pdm, name=name, defaults={'payload_tonnes': capacity})
                if created:
                    record_change(obj, None, {}, 'create')
            for name in ('Основное оборудование', 'Вспомогательная техника'):
                seed(EquipmentAttribute, name=name)
            for name in ('Гарантия', 'Не гарантия'):
                seed(WarrantyAttribute, name=name)
            for name in ('В эксплуатации', 'Списано'):
                seed(EquipmentStatus, name=name, is_active=True)
        self.stdout.write(self.style.SUCCESS('Роль «Специалист НСИ» готова.' + (' Начальные значения добавлены, существующие записи не перезаписаны.' if options['seed'] else '')))
