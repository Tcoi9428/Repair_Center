from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from directories.models import Equipment, EquipmentModel, ReferenceRecord


class MaintenanceType(ReferenceRecord):
    code = models.SlugField('Шифр', max_length=40, unique=True)
    name = models.CharField('Наименование вида обслуживания', max_length=160, unique=True)
    interval_hours = models.PositiveIntegerField('Интервал, моточасы', null=True, blank=True)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Вид технического обслуживания'
        verbose_name_plural = 'Виды технического обслуживания'
        ordering = ['interval_hours', 'name']

    def __str__(self):
        return self.name


class Material(ReferenceRecord):
    nomenclature_number = models.CharField('Номенклатурный номер', max_length=120, blank=True)
    name = models.CharField('Наименование материала', max_length=300)
    default_unit = models.CharField('Единица измерения', max_length=30, default='шт')

    class Meta:
        verbose_name = 'Материал технологической карты'
        verbose_name_plural = 'Материалы технологических карт'
        ordering = ['name', 'nomenclature_number']
        constraints = [
            models.UniqueConstraint(
                Lower('nomenclature_number'),
                condition=~Q(nomenclature_number=''),
                name='maintenance_material_number_ci_unique',
            ),
        ]

    def __str__(self):
        if self.nomenclature_number:
            return f'{self.nomenclature_number} · {self.name}'
        return self.name


class TechnologyCard(ReferenceRecord):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        ACTIVE = 'active', 'Действует'
        ARCHIVED = 'archived', 'Архив'

    name = models.CharField('Наименование технологической карты', max_length=240)
    equipment_model = models.ForeignKey(
        EquipmentModel,
        verbose_name='Модель техники',
        on_delete=models.PROTECT,
        related_name='technology_cards',
    )
    maintenance_type = models.ForeignKey(
        MaintenanceType,
        verbose_name='Вид технического обслуживания',
        on_delete=models.PROTECT,
        related_name='technology_cards',
    )
    revision = models.PositiveIntegerField('Версия карты', default=1, validators=[MinValueValidator(1)])
    status = models.CharField('Статус', max_length=12, choices=Status.choices, default=Status.DRAFT)
    effective_from = models.DateField('Действует с', null=True, blank=True)
    notes = models.TextField('Примечание', blank=True)
    source_name = models.CharField('Источник', max_length=260, blank=True, editable=False)

    class Meta:
        verbose_name = 'Технологическая карта'
        verbose_name_plural = 'Технологические карты'
        ordering = ['equipment_model__name', 'maintenance_type__interval_hours', '-revision']
        constraints = [
            models.UniqueConstraint(
                fields=['equipment_model', 'maintenance_type', 'revision'],
                name='technology_card_model_type_revision_unique',
            ),
            models.UniqueConstraint(
                fields=['equipment_model', 'maintenance_type'],
                condition=Q(status='active'),
                name='one_active_technology_card_per_model_type',
            ),
        ]

    def __str__(self):
        return f'{self.name} · версия {self.revision}'

    @property
    def total_standard_minutes(self):
        value = self.operations.aggregate(total=models.Sum('standard_minutes'))['total']
        return value or 0

    @property
    def total_standard_time_display(self):
        minutes = self.total_standard_minutes
        hours, remainder = divmod(minutes, 60)
        if hours and remainder:
            return f'{hours} ч {remainder} мин'
        if hours:
            return f'{hours} ч'
        return f'{remainder} мин'

    def clean(self):
        super().clean()
        if self.status == self.Status.ACTIVE and not self.effective_from:
            raise ValidationError({'effective_from': 'Для действующей карты укажите дату начала действия.'})


class TechnologyCardOperation(models.Model):
    technology_card = models.ForeignKey(
        TechnologyCard,
        verbose_name='Технологическая карта',
        on_delete=models.CASCADE,
        related_name='operations',
    )
    sequence = models.PositiveIntegerField('Порядок')
    section = models.CharField('Раздел', max_length=200, blank=True)
    operation_number = models.CharField('Номер операции', max_length=30)
    description = models.TextField('Описание операции')
    standard_minutes = models.PositiveIntegerField('Нормативное время, мин', validators=[MinValueValidator(1)])
    is_required = models.BooleanField('Обязательная операция', default=True)

    class Meta:
        verbose_name = 'Операция технологической карты'
        verbose_name_plural = 'Операции технологической карты'
        ordering = ['sequence', 'id']
        constraints = [
            models.UniqueConstraint(fields=['technology_card', 'sequence'], name='technology_operation_sequence_unique'),
            models.UniqueConstraint(
                fields=['technology_card', 'operation_number'],
                name='technology_operation_number_unique',
            ),
        ]

    def __str__(self):
        return f'{self.operation_number}. {self.description}'

    def clean(self):
        self.section = self.section.strip()
        self.operation_number = self.operation_number.strip()
        self.description = self.description.strip()
        if not self.operation_number:
            raise ValidationError({'operation_number': 'Укажите номер операции.'})


class TechnologyCardMaterial(models.Model):
    class Kind(models.TextChoices):
        PART = 'part', 'Запасная часть / расходный материал'
        LUBRICANT = 'lubricant', 'ГСМ / техническая жидкость'

    technology_card = models.ForeignKey(
        TechnologyCard,
        verbose_name='Технологическая карта',
        on_delete=models.CASCADE,
        related_name='required_materials',
    )
    material = models.ForeignKey(
        Material,
        verbose_name='Материал',
        on_delete=models.PROTECT,
        related_name='technology_card_lines',
    )
    sequence = models.PositiveIntegerField('Порядок')
    kind = models.CharField('Категория', max_length=12, choices=Kind.choices, default=Kind.PART)
    quantity = models.DecimalField(
        'Количество',
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    unit = models.CharField('Единица измерения', max_length=30, default='шт')
    notes = models.CharField('Примечание / место применения', max_length=300, blank=True)

    class Meta:
        verbose_name = 'Материал технологической карты'
        verbose_name_plural = 'Материалы технологической карты'
        ordering = ['kind', 'sequence', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['technology_card', 'kind', 'sequence'],
                name='technology_material_sequence_unique',
            ),
        ]

    def __str__(self):
        return f'{self.material}: {self.quantity or "—"} {self.unit}'

    def clean(self):
        self.unit = self.unit.strip()
        self.notes = self.notes.strip()


class EquipmentTechnologyCard(models.Model):
    equipment = models.ForeignKey(
        Equipment,
        verbose_name='Оборудование',
        on_delete=models.CASCADE,
        related_name='technology_card_links',
    )
    technology_card = models.ForeignKey(
        TechnologyCard,
        verbose_name='Технологическая карта',
        on_delete=models.PROTECT,
        related_name='equipment_links',
    )
    assigned_at = models.DateTimeField('Назначена', auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Назначил',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        verbose_name = 'Привязка технологической карты к оборудованию'
        verbose_name_plural = 'Привязки технологических карт к оборудованию'
        ordering = ['technology_card__maintenance_type__interval_hours', 'technology_card__name']
        constraints = [
            models.UniqueConstraint(
                fields=['equipment', 'technology_card'],
                name='equipment_technology_card_unique',
            ),
        ]

    def __str__(self):
        return f'{self.equipment} — {self.technology_card}'

    def clean(self):
        if (
            self.equipment_id
            and self.technology_card_id
            and self.equipment.equipment_model_id != self.technology_card.equipment_model_id
        ):
            raise ValidationError(
                {'technology_card': 'Карта относится к другой модели техники.'}
            )
