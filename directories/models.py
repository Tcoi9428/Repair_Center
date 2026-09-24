import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def add_duration(start, value, unit):
    if not start or not value:
        return start
    if unit == 'days':
        return start + timedelta(days=value)
    month_index = start.month - 1 + value
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

class ReferenceRecord(models.Model):
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Изменил', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        for field in self._meta.fields:
            if isinstance(field, (models.CharField, models.TextField)):
                value = getattr(self, field.name)
                if isinstance(value, str):
                    setattr(self, field.name, value.strip())

class Company(ReferenceRecord):
    code = models.CharField('Код предприятия', max_length=32, unique=True, help_text='Уникальный код. Начальные нули сохраняются.')
    company_name_full = models.CharField('Полное наименование предприятия', max_length=300)
    company_name_top_full = models.CharField('Основное предприятие — полное наименование', max_length=300, blank=True)
    company_name_short = models.CharField('Сокращенное наименование', max_length=120, blank=True)
    company_name_top_short = models.CharField('Основное предприятие — сокращенное наименование', max_length=120, blank=True)
    location_explotation_short = models.CharField('Локация эксплуатации — сокращенно', max_length=120, blank=True)
    company_location = models.CharField('Город / населенный пункт', max_length=200, blank=True)
    company_contact = models.TextField('Контактный адрес', blank=True)
    company_ceo = models.CharField('ФИО руководителя', max_length=200, blank=True)
    service_contract = models.BooleanField('Договор на сервисное обслуживание', default=False)
    service_contract_num = models.CharField('Номер сервисного договора', max_length=120, blank=True, help_text='Можно заполнить позднее, если договор заключен.')

    class Meta:
        verbose_name = 'Предприятие'
        verbose_name_plural = 'Предприятия'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} · {self.company_name_short or self.company_name_full}'

    def clean(self):
        super().clean()
        if self.service_contract_num and not self.service_contract:
            raise ValidationError({'service_contract_num': 'Укажите «Да» для договора или удалите его номер.'})

class EquipmentType(ReferenceRecord):
    name = models.CharField('Наименование типа техники', max_length=200)
    short_name = models.CharField('Сокращенное наименование', max_length=30)
    purpose = models.TextField('Назначение', blank=True)

    class Meta:
        verbose_name = 'Тип техники'
        verbose_name_plural = 'Типы техники'
        ordering = ['name']
        constraints = [models.UniqueConstraint(Lower('name'), name='equipment_type_name_ci_unique'), models.UniqueConstraint(Lower('short_name'), name='equipment_type_short_ci_unique')]

    def __str__(self):
        return f'{self.short_name} · {self.name}'

class EquipmentModel(ReferenceRecord):
    equipment_type = models.ForeignKey(EquipmentType, verbose_name='Тип техники', on_delete=models.PROTECT, related_name='equipment_models')
    name = models.CharField('Наименование модели техники', max_length=200)
    payload_tonnes = models.DecimalField('Грузоподъемность, т', max_digits=9, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(Decimal('0.001'))], help_text='Необязательно. Оставьте пустым, если неприменимо.')

    class Meta:
        verbose_name = 'Модель техники'
        verbose_name_plural = 'Модели техники'
        ordering = ['equipment_type__name', 'name']
        constraints = [models.UniqueConstraint(Lower('name'), 'equipment_type', name='equipment_model_type_name_ci_unique'), models.CheckConstraint(condition=models.Q(payload_tonnes__isnull=True) | models.Q(payload_tonnes__gt=0), name='equipment_payload_positive')]

    def __str__(self):
        return self.name

class EquipmentAttribute(ReferenceRecord):
    name = models.CharField('Наименование признака техники', max_length=120)

    class Meta:
        verbose_name = 'Признак техники'
        verbose_name_plural = 'Признаки техники'
        ordering = ['id']
        constraints = [models.UniqueConstraint(Lower('name'), name='equipment_attribute_name_ci_unique')]

    def __str__(self):
        return self.name

class WarrantyAttribute(ReferenceRecord):
    name = models.CharField('Наименование признака гарантийности', max_length=120)

    class Meta:
        verbose_name = 'Признак гарантийности'
        verbose_name_plural = 'Признаки гарантийности'
        ordering = ['id']
        constraints = [models.UniqueConstraint(Lower('name'), name='warranty_attribute_name_ci_unique')]

    def __str__(self):
        return self.name

class EquipmentStatus(ReferenceRecord):
    name = models.CharField('Наименование статуса', max_length=120)
    is_active = models.BooleanField('Статус активен', default=True, help_text='Неактивный статус остается в справочнике и истории.')

    class Meta:
        verbose_name = 'Статус техники'
        verbose_name_plural = 'Статусы техники'
        ordering = ['-is_active', 'name']
        constraints = [models.UniqueConstraint(Lower('name'), name='equipment_status_name_ci_unique')]

    def __str__(self):
        return self.name


class Equipment(ReferenceRecord):
    DURATION_UNITS = [('days', 'Дни'), ('months', 'Месяцы')]

    equipment_identifier = models.CharField('Идентификатор оборудования', max_length=160, unique=True, editable=False)
    equipment_type = models.ForeignKey(EquipmentType, verbose_name='Тип техники', on_delete=models.PROTECT, related_name='equipment_items')
    equipment_model = models.ForeignKey(EquipmentModel, verbose_name='Модель техники', on_delete=models.PROTECT, related_name='equipment_items')
    status = models.ForeignKey(EquipmentStatus, verbose_name='Статус техники', on_delete=models.PROTECT, related_name='equipment_items')
    owner_company = models.ForeignKey(Company, verbose_name='Предприятие-собственник', on_delete=models.PROTECT, related_name='owned_equipment')
    operating_company = models.ForeignKey(Company, verbose_name='Место эксплуатации', on_delete=models.PROTECT, related_name='operated_equipment')
    factory_number = models.CharField('Заводской номер', max_length=4)
    garage_number = models.CharField('Гаражный / хозяйственный номер', max_length=80, blank=True)
    commissioning_date = models.DateField('Дата ввода в эксплуатацию', null=True, blank=True)
    equipment_image = models.FileField('Изображение техники', upload_to='equipment/images/', blank=True)

    warranty_term_value = models.PositiveIntegerField('Срок гарантии', null=True, blank=True, validators=[MinValueValidator(1)])
    warranty_term_unit = models.CharField('Единица срока гарантии', max_length=10, choices=DURATION_UNITS, blank=True)
    warranty_end_date = models.DateField('Дата окончания гарантии', null=True, blank=True, editable=False)
    warranty_extension_date = models.DateField('Дата продления гарантии', null=True, blank=True)
    warranty_extension_value = models.PositiveIntegerField('Длительность продления гарантии', null=True, blank=True, validators=[MinValueValidator(1)])
    warranty_extension_unit = models.CharField('Единица продления гарантии', max_length=10, choices=DURATION_UNITS, blank=True)

    engine_number = models.CharField('Номер ДВС', max_length=120, blank=True)
    fire_suppression_system = models.CharField('Система АСПТ', max_length=200, blank=True)
    remote_control_installed = models.BooleanField('РДУ установлено', default=False)
    ccs_installed = models.BooleanField('ЦСС установлено', default=False)
    ccs_name = models.CharField('Наименование ЦСС', max_length=200, blank=True)
    control_system = models.CharField('Система управления', max_length=200, blank=True)
    hydraulic_cylinders = models.CharField('Г/Ц', max_length=200, blank=True)

    supply_contract_number = models.CharField('Номер договора поставки', max_length=160, blank=True)
    sale_date = models.DateField('Дата реализации', null=True, blank=True)
    machine_kit_supply_contract = models.FileField('Договор поставки машино-комплекта', upload_to='equipment/contracts/', blank=True)
    operation_manual = models.FileField('Инструкция по эксплуатации', upload_to='equipment/manuals/', blank=True)

    class Meta:
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудование'
        ordering = ['equipment_identifier']

    @property
    def full_name(self):
        garage = self.garage_number or '—'
        return f'{self.equipment_model.name} гар.№ {garage} зав.№{self.factory_number}'

    @property
    def owner_display_name(self):
        return self.owner_company.company_name_top_full or self.owner_company.company_name_full

    @property
    def operating_display_name(self):
        return self.operating_company.company_name_full

    @property
    def warranty_status(self):
        if not self.warranty_end_date:
            return 'Не задано'
        return 'Гарантия' if self.warranty_end_date >= timezone.localdate() else 'Не гарантия'

    @property
    def warranty_term_display(self):
        if not self.warranty_term_value:
            return '—'
        return f'{self.warranty_term_value} {"дн." if self.warranty_term_unit == "days" else "мес."}'

    @property
    def warranty_extension_display(self):
        if not self.warranty_extension_value:
            return '—'
        return f'{self.warranty_extension_value} {"дн." if self.warranty_extension_unit == "days" else "мес."}'

    def __str__(self):
        return self.full_name

    def clean(self):
        super().clean()
        if self.equipment_model_id and self.equipment_type_id and self.equipment_model.equipment_type_id != self.equipment_type_id:
            raise ValidationError({'equipment_model': 'Выбранная модель не относится к указанному типу техники.'})
        if self.owner_company_id and self.owner_company.company_name_top_full and self.owner_company.company_name_full != self.owner_company.company_name_top_full:
            raise ValidationError({'owner_company': 'В качестве собственника выберите основное предприятие.'})
        if self.factory_number:
            if not self.factory_number.isdecimal() or len(self.factory_number) > 4:
                raise ValidationError({'factory_number': 'Укажите от одной до четырех цифр.'})
            self.factory_number = self.factory_number.zfill(4)
        if bool(self.warranty_term_value) != bool(self.warranty_term_unit):
            raise ValidationError({'warranty_term_unit': 'Для срока гарантии укажите значение и единицу измерения.'})
        extension_values = (self.warranty_extension_date, self.warranty_extension_value, self.warranty_extension_unit)
        if any(extension_values) and not all(extension_values):
            raise ValidationError({'warranty_extension_value': 'Для продления укажите дату, длительность и единицу измерения.'})
        self.warranty_end_date = None
        if self.commissioning_date and self.warranty_term_value and self.warranty_term_unit:
            self.warranty_end_date = add_duration(self.commissioning_date, self.warranty_term_value, self.warranty_term_unit)
            if self.warranty_extension_value and self.warranty_extension_unit:
                self.warranty_end_date = add_duration(self.warranty_end_date, self.warranty_extension_value, self.warranty_extension_unit)
        if self.operating_company_id and self.equipment_type_id and self.equipment_model_id and self.factory_number:
            self.equipment_identifier = f'{self.operating_company.code}{self.equipment_type_id}{self.equipment_model_id}{self.factory_number}'


class EquipmentDocument(models.Model):
    equipment = models.ForeignKey(Equipment, verbose_name='Оборудование', on_delete=models.CASCADE, related_name='other_documents')
    title = models.CharField('Название документа', max_length=200)
    file = models.FileField('Файл', upload_to='equipment/documents/')
    uploaded_at = models.DateTimeField('Загружен', auto_now_add=True)

    class Meta:
        verbose_name = 'Документ оборудования'
        verbose_name_plural = 'Документы оборудования'
        ordering = ['title', 'id']

    def __str__(self):
        return self.title

class AuditEntry(models.Model):
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.SET_NULL, null=True, blank=True)
    model_name = models.CharField('Справочник', max_length=80)
    object_id = models.PositiveBigIntegerField('ID записи')
    object_label = models.CharField('Запись', max_length=400)
    action = models.CharField('Действие', max_length=10, choices=[('create', 'Создание'), ('update', 'Изменение'), ('delete', 'Удаление')])
    before = models.JSONField('До', default=dict)
    after = models.JSONField('После', default=dict)

    class Meta:
        verbose_name = 'Изменение справочника'
        verbose_name_plural = 'История изменений'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['model_name', 'object_id'])]
