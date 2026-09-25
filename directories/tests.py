from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse
from openpyxl import Workbook
from .catalog import CATALOGS
from .forms import CompanyForm, EquipmentModelForm, EquipmentForm
from .management.commands.import_pkidp import FIELDS
from .models import Company, Equipment, EquipmentDocument, EquipmentType, EquipmentModel, EquipmentStatus, AuditEntry

class ReferenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_nsi', stdout=StringIO())
        cls.specialist = get_user_model().objects.create_user('nsi-test', password='Test-only-84!Account')
        cls.specialist.groups.add(Group.objects.get(name='Специалист НСИ'))
        cls.outsider = get_user_model().objects.create_user('outsider')
        cls.admin = get_user_model().objects.create_superuser('admin-test', password='Test-only-84!Admin')
        cls.type = EquipmentType.objects.create(name='Погрузочно-доставочная машина', short_name='ПДМ')

    def setUp(self):
        self.client.force_login(self.specialist)

    def url(self, action, slug, pk=None):
        kwargs = {'slug': slug}
        if pk:
            kwargs['pk'] = pk
        return reverse(f'directories:{action}', kwargs=kwargs)

    def test_authentication_and_role_enforced_for_every_endpoint(self):
        anonymous = Client()
        self.assertEqual(anonymous.get('/nsi/').status_code, 302)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get('/nsi/').status_code, 403)
        for catalog in CATALOGS:
            with self.subTest(slug=catalog.slug):
                self.assertEqual(self.client.get(self.url('list', catalog.slug)).status_code, 403)
                self.assertEqual(self.client.get(self.url('create', catalog.slug)).status_code, 403)
                self.assertEqual(self.client.post(self.url('create', catalog.slug), {'name':'Injected'}).status_code, 403)
                self.assertEqual(self.client.post(self.url('edit', catalog.slug, 1), {'name':'Injected'}).status_code, 403)

    def test_create_and_edit_reference_catalogs_and_audit(self):
        data = {
            'companies': {'code':'0017','company_name_full':'Предприятие А','service_contract':'True','service_contract_num':''},
            'equipment-types': {'name':'Самоходная буровая установка','short_name':'СБУ','purpose':'Бурение'},
            'equipment-models': {'equipment_type':self.type.pk,'name':'ПДМ 14 Исеть','payload_tonnes':'14,5'},
            'equipment-attributes': {'name':'Основное оборудование'},
            'warranty-attributes': {'name':'Гарантия'},
            'equipment-statuses': {'name':'В эксплуатации','is_active':'on'},
            'maintenance-types': {'code':'TO-250','name':'ТО-250','interval_hours':'250','description':'Регламентное ТО','is_active':'on'},
            'materials': {'nomenclature_number':'TEST-001','name':'Тестовый фильтр','default_unit':'шт'},
        }
        for catalog in CATALOGS:
            if catalog.slug == 'equipment':
                continue
            with self.subTest(slug=catalog.slug):
                response = self.client.post(self.url('create', catalog.slug), data[catalog.slug])
                self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
                record = catalog.model.objects.latest('id')
                self.assertEqual(record.updated_by_id, self.specialist.pk)
                self.assertContains(self.client.get(self.url('detail', catalog.slug, record.pk)), 'История изменений')
                self.assertEqual(self.client.get(self.url('list', catalog.slug)).status_code, 200)
                edited = dict(data[catalog.slug], expected_version=1)
                key = 'company_name_full' if catalog.slug == 'companies' else 'name'
                edited[key] += ' изменено'
                response = self.client.post(self.url('edit', catalog.slug, record.pk), edited)
                self.assertEqual(response.status_code, 302)
                record.refresh_from_db()
                self.assertEqual(record.version, 2)
                self.assertEqual(getattr(record, key), edited[key])
                events = AuditEntry.objects.filter(model_name=catalog.model._meta.model_name, object_id=record.pk)
                self.assertEqual(events.count(), 2)
                self.assertEqual(events.first().before[key], data[catalog.slug][key])
        self.assertTrue(Company.objects.filter(code='0017').exists())
        self.assertEqual(str(EquipmentModel.objects.get().payload_tonnes), '14.500')

    def test_equipment_card_identifier_warranty_tabs_documents_and_permissions(self):
        company = Company.objects.create(code='1000', company_name_full='АО Рудник', company_name_top_full='АО Рудник', company_name_short='АР')
        site = Company.objects.create(code='1001', company_name_full='Шахта Северная', company_name_top_full='АО Рудник', company_name_short='ШС')
        model = EquipmentModel.objects.create(equipment_type=self.type, name='ПДМ 10 ШААЗ', payload_tonnes=10)
        status = EquipmentStatus.objects.create(name='В эксплуатации')
        payload = {
            'equipment_type': self.type.pk,
            'equipment_model': model.pk,
            'status': status.pk,
            'owner_company': company.pk,
            'operating_company': site.pk,
            'factory_number': '20',
            'garage_number': '265',
            'commissioning_date': '2025-01-31',
            'warranty_term_value': '1',
            'warranty_term_unit': 'months',
            'warranty_extension_date': '2025-02-20',
            'warranty_extension_value': '10',
            'warranty_extension_unit': 'days',
            'documents-TOTAL_FORMS': '2',
            'documents-INITIAL_FORMS': '0',
            'documents-MIN_NUM_FORMS': '0',
            'documents-MAX_NUM_FORMS': '1000',
            'documents-0-title': 'Паспорт машины',
            'documents-0-file': SimpleUploadedFile('passport.txt', b'equipment passport'),
            'documents-1-title': '',
        }
        response = self.client.post(self.url('create', 'equipment'), payload)
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
        item = Equipment.objects.get()
        self.assertEqual(item.factory_number, '0020')
        self.assertEqual(item.equipment_identifier, f'1001{self.type.pk}{model.pk}0020')
        self.assertEqual(item.full_name, 'ПДМ 10 ШААЗ гар.№ 265 зав.№0020')
        self.assertEqual(item.warranty_end_date, date(2025, 3, 10))
        self.assertEqual(item.warranty_status, 'Не гарантия')
        document = EquipmentDocument.objects.get(equipment=item)
        self.assertEqual(document.title, 'Паспорт машины')
        card = self.client.get(self.url('detail', 'equipment', item.pk))
        self.assertContains(card, 'ПДМ 10 ШААЗ гар.№ 265 зав.№0020')
        self.assertContains(card, 'equipment-title-single-line')
        self.assertContains(card, '<dt>Предприятие-собственник</dt><dd>АО Рудник</dd>', html=True)
        self.assertContains(card, '<dt>Место эксплуатации</dt><dd>Шахта Северная</dd>', html=True)
        for tab in ('Основное', 'Условия гарантии', 'Установленные узлы', 'Документы'):
            self.assertContains(card, tab)
        self.assertContains(card, 'Паспорт машины')
        self.outsider.user_permissions.add(Permission.objects.get(codename='view_equipment'))
        self.client.force_login(self.outsider)
        readonly = self.client.get(self.url('detail', 'equipment', item.pk))
        self.assertEqual(readonly.status_code, 200)
        self.assertNotContains(readonly, 'Редактировать')
        document.file.delete(save=False)

    def test_equipment_rejects_model_from_another_type(self):
        company = Company.objects.create(code='1001', company_name_full='АО Рудник')
        other_type = EquipmentType.objects.create(name='Шахтный автосамосвал', short_name='ШАС')
        wrong_model = EquipmentModel.objects.create(equipment_type=other_type, name='ШАС 30')
        status = EquipmentStatus.objects.create(name='В эксплуатации')
        form = EquipmentForm({
            'equipment_type': self.type.pk,
            'equipment_model': wrong_model.pk,
            'status': status.pk,
            'owner_company': company.pk,
            'operating_company': company.pk,
            'factory_number': '12',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('equipment_model', form.errors)

    def test_concurrent_edit_preserves_first_save(self):
        record = EquipmentStatus.objects.create(name='В эксплуатации')
        url = self.url('edit', 'equipment-statuses', record.pk)
        self.assertEqual(self.client.post(url, {'name':'В резерве','is_active':'on','expected_version':1}).status_code, 302)
        response = self.client.post(url, {'name':'Списано','is_active':'on','expected_version':1})
        self.assertContains(response, 'Запись уже изменил другой пользователь')
        record.refresh_from_db()
        self.assertEqual(record.name, 'В резерве')
        self.assertEqual(record.version, 2)
        self.assertEqual(AuditEntry.objects.filter(model_name='equipmentstatus').count(), 1)

    def test_duplicate_names_are_case_insensitive_in_postgresql(self):
        EquipmentStatus.objects.create(name='В эксплуатации')
        response = self.client.post(self.url('create', 'equipment-statuses'), {'name':'в эксплуатации','is_active':'on'})
        self.assertContains(response, 'Не удалось сохранить')
        self.assertEqual(EquipmentStatus.objects.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EquipmentStatus.objects.create(name='В ЭКСПЛУАТАЦИИ')

    def test_company_code_unique_but_short_names_may_repeat(self):
        Company.objects.create(code='100', company_name_full='Компания 1', company_name_short='СТС')
        payload = {'code':'100','company_name_full':'Компания 2','company_name_short':'СТС','service_contract':'False'}
        self.assertFalse(CompanyForm(payload).is_valid())
        payload['code'] = '101'
        self.assertTrue(CompanyForm(payload).is_valid())

    def test_payload_optional_positive_localized_and_type_required(self):
        base = {'name':'Модель А','equipment_type':self.type.pk,'payload_tonnes':''}
        form = EquipmentModelForm(base)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save().payload_tonnes)
        for value in ('0', '-2', 'текст'):
            self.assertFalse(EquipmentModelForm(dict(base, name='Модель Б', payload_tonnes=value)).is_valid())
        self.assertFalse(EquipmentModelForm(dict(base, equipment_type='')).is_valid())
        self.assertFalse(EquipmentModelForm(dict(base, equipment_type=999999)).is_valid())
        with self.assertRaises(ProtectedError):
            self.type.delete()

    def test_contract_validation_does_not_drop_number(self):
        data = {'code':'010','company_name_full':'Компания','service_contract':'False','service_contract_num':'Д-17'}
        form = CompanyForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('service_contract_num', form.errors)
        self.assertTrue(CompanyForm(dict(data, service_contract='True')).is_valid())
        self.assertTrue(CompanyForm(dict(data, service_contract='True', service_contract_num='')).is_valid())

    def test_status_deactivation_and_filters(self):
        a = EquipmentStatus.objects.create(name='В эксплуатации')
        b = EquipmentStatus.objects.create(name='Списано', is_active=False)
        response = self.client.get(self.url('list','equipment-statuses'), {'state':'inactive'})
        self.assertContains(response, 'Списано')
        self.assertNotContains(response, '>В эксплуатации<')
        response = self.client.post(self.url('edit','equipment-statuses',a.pk), {'name':a.name,'expected_version':1})
        self.assertEqual(response.status_code,302)
        a.refresh_from_db()
        self.assertFalse(a.is_active)

    def test_model_filter_search_pagination_and_safe_render(self):
        for number in range(25):
            Company.objects.create(code=f'{number:04}', company_name_full=f'Компания {number}')
        response = self.client.get(self.url('list','companies'), {'page':2})
        self.assertEqual(len(response.context['page_obj']), 5)
        response = self.client.get(self.url('list','companies'), {'q':'0001'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        Company.objects.create(code='JS', company_name_full='<script>alert(1)</script>')
        self.assertContains(self.client.get(self.url('list','companies'), {'q':'JS'}), '&lt;script&gt;')
        other = EquipmentType.objects.create(name='Другой тип',short_name='ДТ')
        EquipmentModel.objects.create(name='Модель',equipment_type=other)
        response = self.client.get(self.url('list','equipment-models'), {'type':self.type.pk})
        self.assertEqual(response.context['page_obj'].paginator.count,0)

    def test_view_only_permission_does_not_allow_writes(self):
        self.outsider.user_permissions.add(Permission.objects.get(codename='view_company'))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url('list','companies')).status_code,200)
        self.assertEqual(self.client.post(self.url('create','companies'),{}).status_code,403)

    def test_visual_cards_row_navigation_and_edit_button_follow_permissions(self):
        company = Company.objects.create(code='CARD-1', company_name_full='Карточка предприятия')
        AuditEntry.objects.create(
            actor=None,
            model_name='company',
            object_id=company.pk,
            action='create',
            before={},
            after={'code': company.code},
        )
        model = EquipmentModel.objects.create(name='ПДМ карточка', equipment_type=self.type, payload_tonnes=14)
        company_list = self.client.get(self.url('list','companies'))
        self.assertContains(company_list, f'data-row-href="{self.url("detail","companies",company.pk)}"')
        company_card = self.client.get(self.url('detail','companies',company.pk))
        self.assertContains(company_card,'record-hero-company')
        self.assertContains(company_card,'Предприятия · Код: CARD-1')
        self.assertContains(company_card,'Редактировать')
        self.assertContains(company_card,'Начальная загрузка')
        content = company_card.content.decode()
        labels = [
            'Код предприятия', 'Наименование предприятия', 'Основное предприятие',
            'Сокращенное наименование', 'Город / населенный пункт',
            'Договор на сервисное обслуживание', 'Номер сервисного договора',
            'Контактный адрес', 'ФИО руководителя',
        ]
        positions = [content.index(f'<dt>{label}</dt>') for label in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertNotContains(company_card, 'Основное предприятие — сокращенное наименование')
        self.assertNotContains(company_card, 'Локация эксплуатации — сокращенно')
        self.assertContains(self.client.get(self.url('detail','equipment-types',self.type.pk)),'record-hero-pdm')
        self.assertContains(self.client.get(self.url('detail','equipment-models',model.pk)),'record-hero-pdm')
        self.outsider.user_permissions.add(Permission.objects.get(codename='view_company'))
        self.client.force_login(self.outsider)
        readonly = self.client.get(self.url('detail','companies',company.pk))
        self.assertEqual(readonly.status_code,200)
        self.assertNotContains(readonly,'Редактировать')

    def test_csrf_and_post_only_logout(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.specialist)
        self.assertEqual(client.post(self.url('create','equipment-statuses'), {'name':'Hack'}).status_code,403)
        self.assertEqual(client.get('/logout/').status_code,405)

    def test_admin_forms_and_audit_readonly(self):
        self.client.force_login(self.admin)
        for catalog in CATALOGS:
            self.assertEqual(
                self.client.get(
                    reverse(
                        f'admin:{catalog.model._meta.app_label}_{catalog.model._meta.model_name}_add'
                    )
                ).status_code,
                200,
            )
        self.assertEqual(self.client.get(reverse('admin:directories_auditentry_add')).status_code,403)
        record = EquipmentStatus.objects.create(name='Начальный')
        url = reverse('admin:directories_equipmentstatus_change', args=[record.pk])
        self.assertEqual(self.client.post(url, {'name':'Принятый','is_active':'on','expected_version':1,'_save':'Сохранить'}).status_code,302)
        response = self.client.post(url, {'name':'Устаревший','is_active':'on','expected_version':1,'_save':'Сохранить'})
        self.assertContains(response,'Запись уже изменена')
        record.refresh_from_db()
        self.assertEqual(record.name,'Принятый')

    def test_seed_is_repeatable_and_preserves_existing_edits(self):
        call_command('setup_nsi','--seed',stdout=StringIO())
        original = EquipmentType.objects.get(short_name='СБУ')
        original.purpose='Уточненное назначение'
        original.save()
        call_command('setup_nsi','--seed',stdout=StringIO())
        self.assertEqual(EquipmentType.objects.count(),4)
        self.assertEqual(EquipmentModel.objects.count(),4)
        original.refresh_from_db()
        self.assertEqual(original.purpose,'Уточненное назначение')

    def test_import_dry_run_repeat_and_atomic_rollback(self):
        # Generated XLSX is only a disposable test fixture, never a user artifact.
        temp_root = Path(__file__).resolve().parent.parent / '.local' / 'test-tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=temp_root) as folder:
            path=Path(folder)/'input.xlsx'
            book=Workbook()
            sheet=book.active
            sheet.append(FIELDS)
            sheet.append(['0010','Компания',None,'К',None,None,None,None,None,'Да',None])
            book.save(path)
            call_command('import_pkidp',str(path),'--dry-run',stdout=StringIO())
            self.assertEqual(Company.objects.count(),0)
            call_command('import_pkidp',str(path),stdout=StringIO())
            call_command('import_pkidp',str(path),stdout=StringIO())
            self.assertEqual(Company.objects.count(),1)
            self.assertEqual(Company.objects.get().code,'0010')
            sheet.append(['0020','Компания Б',None,None,None,None,None,None,None,'Нет',None])
            sheet.append(['0030','Компания В',None,None,None,None,None,None,None,'Ошибка',None])
            book.save(path)
            with self.assertRaises(CommandError):
                call_command('import_pkidp',str(path),stdout=StringIO())
            self.assertEqual(Company.objects.count(),1)
