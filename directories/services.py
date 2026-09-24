from django.core.exceptions import ValidationError
from django.db import transaction
from .models import AuditEntry

class ConcurrentEdit(ValidationError):
    pass

def snapshot(instance):
    return {field.name: field.value_to_string(instance) for field in instance._meta.fields if field.name not in {'created_at', 'updated_at', 'updated_by', 'version'}}

def record_change(instance, actor, before, action):
    AuditEntry.objects.create(actor=actor, model_name=instance._meta.model_name, object_id=instance.pk,
                              object_label=str(instance)[:400], action=action, before=before, after=snapshot(instance))

@transaction.atomic
def save_record(form, actor):
    candidate = form.save(commit=False)
    before = {}
    action = 'create'
    if candidate.pk:
        current = type(candidate).objects.select_for_update().get(pk=candidate.pk)
        if current.version != form.cleaned_data['expected_version']:
            raise ConcurrentEdit('Запись уже изменил другой пользователь. Откройте актуальную карточку и повторите изменения.')
        before = snapshot(current)
        candidate.version = current.version + 1
        action = 'update'
    candidate.updated_by = actor
    candidate.full_clean()
    candidate.save()
    record_change(candidate, actor, before, action)
    return candidate

