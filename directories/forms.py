from django import forms
from django.db.models import F, Q
from .models import (
    Company, EquipmentType, EquipmentModel, EquipmentAttribute, WarrantyAttribute,
    EquipmentStatus, Equipment, EquipmentDocument,
)

class ReferenceForm(forms.ModelForm):
    expected_version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['expected_version'].initial = self.instance.version
            self.fields['expected_version'].required = True
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['rows'] = 3
            field.widget.attrs['class'] = 'form-control'

class CompanyForm(ReferenceForm):
    service_contract = forms.TypedChoiceField(label='Договор на сервисное обслуживание', choices=[('False', 'Нет'), ('True', 'Да')], coerce=lambda value: value == 'True')
    class Meta:
        model = Company
        fields = ['code', 'company_name_full', 'company_name_short', 'company_name_top_full', 'company_name_top_short', 'location_explotation_short', 'company_location', 'company_contact', 'company_ceo', 'service_contract', 'service_contract_num']

class EquipmentTypeForm(ReferenceForm):
    class Meta:
        model = EquipmentType
        fields = ['name', 'short_name', 'purpose']

class EquipmentModelForm(ReferenceForm):
    class Meta:
        model = EquipmentModel
        fields = ['equipment_type', 'name', 'payload_tonnes']
        localized_fields = ['payload_tonnes']

class EquipmentAttributeForm(ReferenceForm):
    class Meta:
        model = EquipmentAttribute
        fields = ['name']

class WarrantyAttributeForm(ReferenceForm):
    class Meta:
        model = WarrantyAttribute
        fields = ['name']

class EquipmentStatusForm(ReferenceForm):
    class Meta:
        model = EquipmentStatus
        fields = ['name', 'is_active']


class EquipmentModelSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-equipment-type'] = value.instance.equipment_type_id
        return option


class EquipmentForm(ReferenceForm):
    class Meta:
        model = Equipment
        fields = [
            'equipment_type', 'equipment_model', 'status', 'owner_company', 'operating_company',
            'factory_number', 'garage_number', 'commissioning_date', 'equipment_image',
            'warranty_term_value', 'warranty_term_unit', 'warranty_extension_date',
            'warranty_extension_value', 'warranty_extension_unit', 'engine_number',
            'fire_suppression_system', 'remote_control_installed', 'ccs_installed', 'ccs_name',
            'control_system', 'hydraulic_cylinders', 'supply_contract_number', 'sale_date',
            'machine_kit_supply_contract', 'operation_manual',
        ]
        widgets = {
            'equipment_model': EquipmentModelSelect(),
            'commissioning_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_extension_date': forms.DateInput(attrs={'type': 'date'}),
            'sale_date': forms.DateInput(attrs={'type': 'date'}),
            'equipment_image': forms.FileInput(attrs={'accept': 'image/*'}),
        }
        help_texts = {
            'factory_number': 'От одной до четырех цифр. Система дополнит номер ведущими нулями.',
            'equipment_image': 'Изображение используется как фон карточки оборудования.',
            'warranty_term_value': 'Укажите вместе с единицей измерения.',
            'warranty_extension_value': 'Заполняется вместе с датой и единицей продления.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipment_model'].queryset = EquipmentModel.objects.select_related('equipment_type').all()
        self.fields['status'].queryset = EquipmentStatus.objects.filter(is_active=True) | EquipmentStatus.objects.filter(pk=getattr(self.instance, 'status_id', None))
        self.fields['owner_company'].queryset = Company.objects.filter(
            Q(company_name_top_full='') | Q(company_name_full=F('company_name_top_full'))
        )
        self.fields['operating_company'].queryset = Company.objects.all()


EquipmentDocumentFormSet = forms.inlineformset_factory(
    Equipment,
    EquipmentDocument,
    fields=['title', 'file'],
    extra=2,
    can_delete=True,
    widgets={'file': forms.FileInput()},
)
