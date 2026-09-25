from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from directories.models import Company, Equipment, EquipmentModel, EquipmentStatus, EquipmentType

from .importers import parse_workbook
from .models import (
    EquipmentTechnologyCard,
    MaintenanceType,
    Material,
    TechnologyCard,
    TechnologyCardMaterial,
    TechnologyCardOperation,
)


class TechnologyCardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_nsi', stdout=StringIO())
        cls.specialist = get_user_model().objects.create_user('technology-nsi', password='Test-only-84!Account')
        cls.specialist.groups.add(Group.objects.get(name='Специалист НСИ'))
        cls.outsider = get_user_model().objects.create_user('technology-outsider')
        equipment_type = EquipmentType.objects.create(name='Погрузочно-доставочная машина', short_name='ПДМ')
        cls.model = EquipmentModel.objects.create(equipment_type=equipment_type, name='ПДМ 10 ШААЗ', payload_tonnes=10)
        cls.other_model = EquipmentModel.objects.create(equipment_type=equipment_type, name='ПДМ 14 ШААЗ', payload_tonnes=14)
        status = EquipmentStatus.objects.create(name='В эксплуатации', is_active=True)
        company = Company.objects.create(code='1000', company_name_full='АО Рудник', company_name_top_full='АО Рудник')
        cls.equipment = Equipment.objects.create(
            equipment_identifier='1000110020',
            equipment_type=equipment_type,
            equipment_model=cls.model,
            status=status,
            owner_company=company,
            operating_company=company,
            factory_number='0020',
            garage_number='265',
        )
        cls.maintenance_type = MaintenanceType.objects.create(code='TO-250', name='ТО-250', interval_hours=250)
        cls.material = Material.objects.create(
            nomenclature_number='548-10-11001-6-01',
            name='Масляный фильтр двигателя',
            default_unit='шт',
        )
        cls.card = TechnologyCard.objects.create(
            name='ТО-250 · ПДМ 10 ШААЗ',
            equipment_model=cls.model,
            maintenance_type=cls.maintenance_type,
            revision=1,
        )
        TechnologyCardOperation.objects.create(
            technology_card=cls.card,
            sequence=1,
            section='ДВИГАТЕЛЬ',
            operation_number='1',
            description='Заменить моторное масло.',
            standard_minutes=45,
        )
        TechnologyCardMaterial.objects.create(
            technology_card=cls.card,
            material=cls.material,
            sequence=1,
            kind='part',
            quantity=1,
            unit='шт',
        )

    def setUp(self):
        self.client.force_login(self.specialist)

    def test_permissions_protect_all_card_endpoints(self):
        anonymous = Client()
        self.assertEqual(anonymous.get(reverse('maintenance:card_list')).status_code, 302)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse('maintenance:card_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('maintenance:card_detail', args=[self.card.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('maintenance:card_create')).status_code, 403)

    def test_card_detail_shows_operations_materials_and_total(self):
        response = self.client.get(reverse('maintenance:card_detail', args=[self.card.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ДВИГАТЕЛЬ')
        self.assertContains(response, 'Заменить моторное масло.')
        self.assertContains(response, '548-10-11001-6-01')
        self.assertContains(response, '45 мин')

    def test_create_card_with_operation(self):
        data = {
            'name': 'ТО-500 · ПДМ 10 ШААЗ',
            'equipment_model': self.model.pk,
            'maintenance_type': self.maintenance_type.pk,
            'revision': 2,
            'status': 'draft',
            'effective_from': '',
            'notes': '',
            'operations-TOTAL_FORMS': 1,
            'operations-INITIAL_FORMS': 0,
            'operations-MIN_NUM_FORMS': 0,
            'operations-MAX_NUM_FORMS': 1000,
            'operations-0-sequence': 1,
            'operations-0-section': 'ОБЩИЕ РАБОТЫ',
            'operations-0-operation_number': '1',
            'operations-0-description': 'Проверить состояние техники.',
            'operations-0-standard_minutes': 10,
            'operations-0-is_required': 'on',
            'materials-TOTAL_FORMS': 0,
            'materials-INITIAL_FORMS': 0,
            'materials-MIN_NUM_FORMS': 0,
            'materials-MAX_NUM_FORMS': 1000,
        }
        response = self.client.post(reverse('maintenance:card_create'), data)
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
        created = TechnologyCard.objects.get(revision=2)
        self.assertEqual(created.operations.count(), 1)
        self.assertEqual(created.updated_by, self.specialist)

    def test_equipment_assignment_accepts_only_matching_model(self):
        response = self.client.post(
            reverse('maintenance:equipment_assignments', args=[self.equipment.pk]),
            {'technology_cards': [self.card.pk]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            EquipmentTechnologyCard.objects.filter(equipment=self.equipment, technology_card=self.card).exists()
        )
        other_card = TechnologyCard.objects.create(
            name='Чужая карта',
            equipment_model=self.other_model,
            maintenance_type=self.maintenance_type,
            revision=1,
        )
        response = self.client.post(
            reverse('maintenance:equipment_assignments', args=[self.equipment.pk]),
            {'technology_cards': [other_card.pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('technology_cards', response.context['form'].errors)


class TechnologyCardImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        equipment_type = EquipmentType.objects.create(name='Погрузочно-доставочная машина', short_name='ПДМ')
        cls.model = EquipmentModel.objects.create(equipment_type=equipment_type, name='ПДМ 10 ШААЗ', payload_tonnes=10)
        status = EquipmentStatus.objects.create(name='В эксплуатации', is_active=True)
        company = Company.objects.create(code='1000', company_name_full='АО Рудник', company_name_top_full='АО Рудник')
        cls.equipment = Equipment.objects.create(
            equipment_identifier='1000110020', equipment_type=equipment_type, equipment_model=cls.model,
            status=status, owner_company=company, operating_company=company,
            factory_number='0020', garage_number='265',
        )

    @property
    def source(self):
        return Path(settings.BASE_DIR) / 'source-documents' / 'pdm10-maintenance-checklists-v6.xlsx'

    def test_parser_extracts_all_source_cards(self):
        cards = parse_workbook(self.source)
        self.assertEqual([card.interval_hours for card in cards], [250, 500, 1000, 2000, 6000, 10000])
        self.assertEqual([len(card.operations) for card in cards], [60, 70, 84, 87, 91, 100])
        self.assertEqual(cards[0].operations[0].operation_number, '1')
        self.assertEqual(cards[0].operations[0].section, 'ОБЩИЕ РАБОТЫ')
        self.assertEqual(cards[0].total_minutes, 534)

    def test_command_imports_and_assigns_cards_idempotently(self):
        output = StringIO()
        call_command('import_technology_cards', str(self.source), assign_existing=True, stdout=output)
        self.assertEqual(TechnologyCard.objects.count(), 6)
        self.assertEqual(TechnologyCardOperation.objects.count(), 492)
        self.assertEqual(EquipmentTechnologyCard.objects.filter(equipment=self.equipment).count(), 6)
        call_command('import_technology_cards', str(self.source), assign_existing=True, stdout=output)
        self.assertEqual(TechnologyCard.objects.count(), 6)
        self.assertIn('пропущено: 6', output.getvalue().lower())
