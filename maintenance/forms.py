from django import forms
from django.forms.models import BaseInlineFormSet

from directories.forms import ReferenceForm

from .models import (
    MaintenanceType,
    Material,
    TechnologyCard,
    TechnologyCardMaterial,
    TechnologyCardOperation,
)


class MaintenanceTypeForm(ReferenceForm):
    class Meta:
        model = MaintenanceType
        fields = ['code', 'name', 'interval_hours', 'description', 'is_active']


class MaterialForm(ReferenceForm):
    class Meta:
        model = Material
        fields = ['nomenclature_number', 'name', 'default_unit']


class TechnologyCardForm(ReferenceForm):
    class Meta:
        model = TechnologyCard
        fields = [
            'name',
            'equipment_model',
            'maintenance_type',
            'revision',
            'status',
            'effective_from',
            'notes',
        ]
        widgets = {
            'effective_from': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class TechnologyCardOperationForm(forms.ModelForm):
    class Meta:
        model = TechnologyCardOperation
        fields = ['sequence', 'section', 'operation_number', 'description', 'standard_minutes', 'is_required']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class TechnologyCardMaterialForm(forms.ModelForm):
    class Meta:
        model = TechnologyCardMaterial
        fields = ['sequence', 'kind', 'material', 'quantity', 'unit', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class RequiredOperationFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE') and form.cleaned_data.get('description')
        ]
        if not active:
            raise forms.ValidationError('Добавьте хотя бы одну операцию технологической карты.')


TechnologyCardOperationFormSet = forms.inlineformset_factory(
    TechnologyCard,
    TechnologyCardOperation,
    form=TechnologyCardOperationForm,
    formset=RequiredOperationFormSet,
    extra=3,
    can_delete=True,
)

TechnologyCardMaterialFormSet = forms.inlineformset_factory(
    TechnologyCard,
    TechnologyCardMaterial,
    form=TechnologyCardMaterialForm,
    extra=3,
    can_delete=True,
)


class EquipmentTechnologyCardForm(forms.Form):
    technology_cards = forms.ModelMultipleChoiceField(
        queryset=TechnologyCard.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Технологические карты',
    )

    def __init__(self, *args, equipment, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = TechnologyCard.objects.filter(equipment_model=equipment.equipment_model).select_related(
            'maintenance_type', 'equipment_model'
        )
        self.fields['technology_cards'].queryset = queryset
        self.fields['technology_cards'].initial = equipment.technology_card_links.values_list(
            'technology_card_id', flat=True
        )
