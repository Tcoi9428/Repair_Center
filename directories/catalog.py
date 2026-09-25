from dataclasses import dataclass
from . import forms, models
from maintenance import forms as maintenance_forms
from maintenance import models as maintenance_models

@dataclass(frozen=True)
class Catalog:
    slug: str
    title: str
    singular: str
    description: str
    model: type
    form: type
    columns: tuple
    search_fields: tuple
    icon: str = 'book'

    def permission(self, action):
        return f'{self.model._meta.app_label}.{action}_{self.model._meta.model_name}'

CATALOGS = [
    Catalog('equipment', 'Оборудование', 'оборудование', 'Единицы техники, их эксплуатация, гарантия, установленные узлы и документы.', models.Equipment, forms.EquipmentForm,
            ('equipment_identifier', 'equipment_model', 'garage_number', 'factory_number', 'operating_company', 'status'),
            ('equipment_identifier', 'equipment_model__name', 'garage_number', 'factory_number', 'operating_company__company_name_full'), 'machine'),
    Catalog('companies', 'Предприятия', 'предприятие', 'Предприятия и площадки, где эксплуатируется техника.', models.Company, forms.CompanyForm,
            ('code', 'company_name_full', 'company_name_short', 'company_location', 'service_contract'),
            ('code', 'company_name_full', 'company_name_short', 'company_name_top_full', 'company_location', 'location_explotation_short'), 'company'),
    Catalog('equipment-types', 'Типы техники', 'тип техники', 'Классификация техники и ее назначение.', models.EquipmentType, forms.EquipmentTypeForm,
            ('id', 'name', 'short_name', 'purpose'), ('name', 'short_name', 'purpose'), 'type'),
    Catalog('equipment-models', 'Модели техники', 'модель техники', 'Модели по типам техники и грузоподъемность.', models.EquipmentModel, forms.EquipmentModelForm,
            ('id', 'name', 'equipment_type', 'payload_tonnes'), ('name', 'equipment_type__name', 'equipment_type__short_name'), 'model'),
    Catalog('equipment-attributes', 'Признаки техники', 'признак техники', 'Основное оборудование и вспомогательная техника.', models.EquipmentAttribute, forms.EquipmentAttributeForm,
            ('id', 'name'), ('name',), 'tag'),
    Catalog('warranty-attributes', 'Признаки гарантийности', 'признак гарантийности', 'Гарантийная принадлежность оборудования.', models.WarrantyAttribute, forms.WarrantyAttributeForm,
            ('id', 'name'), ('name',), 'shield'),
    Catalog('equipment-statuses', 'Статусы техники', 'статус техники', 'Состояния жизненного цикла и доступность статусов.', models.EquipmentStatus, forms.EquipmentStatusForm,
            ('id', 'name', 'is_active'), ('name',), 'status'),
    Catalog('maintenance-types', 'Виды технического обслуживания', 'вид технического обслуживания', 'Интервалы и виды регламентного обслуживания и ремонта.', maintenance_models.MaintenanceType, maintenance_forms.MaintenanceTypeForm,
            ('id', 'code', 'name', 'interval_hours', 'is_active'), ('code', 'name', 'description'), 'wrench'),
    Catalog('materials', 'Материалы и запасные части', 'материал', 'Номенклатура, используемая в технологических картах.', maintenance_models.Material, maintenance_forms.MaterialForm,
            ('id', 'nomenclature_number', 'name', 'default_unit'), ('nomenclature_number', 'name'), 'box'),
]
BY_SLUG = {item.slug: item for item in CATALOGS}
