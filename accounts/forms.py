from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from .models import Role, RoleRequest

def available_permissions():
    return Permission.objects.filter(
        content_type__app_label__in=['directories', 'maintenance'],
        codename__regex=r'^(view|add|change)_',
    ).exclude(
        content_type__model__in=[
            'auditentry', 'equipmentdocument', 'technologycardoperation',
            'technologycardmaterial', 'equipmenttechnologycard',
        ]
    ).order_by('content_type__app_label', 'content_type__model', 'codename')

class PermissionChoice(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        action = {'view':'Просмотр', 'add':'Создание', 'change':'Редактирование'}[obj.codename.split('_')[0]]
        return f'{obj.content_type.name} — {action}'

class RoleForm(forms.ModelForm):
    permissions = PermissionChoice(queryset=Permission.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label='Доступные экраны и действия')
    expected_version = forms.IntegerField(widget=forms.HiddenInput)
    class Meta:
        model = Role
        fields = ['name', 'scope']
        widgets = {'scope': forms.Textarea(attrs={'rows':3})}
        labels = {'scope':'Описание назначения роли (права задаются ниже)'}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].queryset = available_permissions()
        self.fields['permissions'].initial = self.instance.group.permissions.filter(pk__in=available_permissions()).values_list('pk',flat=True)
        self.fields['expected_version'].initial = self.instance.version

    def clean_permissions(self):
        selected = self.cleaned_data['permissions']
        codes = set(selected.values_list('codename', flat=True))
        for permission in selected:
            action, model = permission.codename.split('_', 1)
            if action in ('add','change') and f'view_{model}' not in codes:
                raise forms.ValidationError('Для создания и редактирования нужно также разрешить просмотр соответствующего справочника.')
        return selected

class RequestForm(forms.ModelForm):
    class Meta:
        model = RoleRequest
        fields = ['role', 'reason']
        labels = {'role':'Запрашиваемая роль', 'reason':'Для каких задач нужен доступ'}
        widgets = {'reason':forms.Textarea(attrs={'rows':4})}
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        pending = user.role_requests.filter(status='pending').values_list('role_id', flat=True)
        self.fields['role'].queryset = Role.objects.exclude(group__in=user.groups.all()).exclude(pk__in=pending)
        self.fields['role'].empty_label = 'Выберите роль'

class DecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=[('approved','Согласовать'),('rejected','Отклонить')], label='Решение')
    comment = forms.CharField(max_length=2000, required=False, label='Комментарий', widget=forms.Textarea(attrs={'rows':3}))
    def clean(self):
        data = super().clean()
        if data.get('decision') == 'rejected' and not data.get('comment'):
            self.add_error('comment','Укажите причину отклонения.')
        return data

class NewUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email']

class MembershipForm(forms.Form):
    role = forms.ModelChoiceField(queryset=Role.objects.all(), label='Роль')
    action = forms.ChoiceField(choices=[('grant','Предоставить'),('revoke','Отозвать')], label='Действие')
    reason = forms.CharField(max_length=2000, label='Основание', widget=forms.Textarea(attrs={'rows':3}))
