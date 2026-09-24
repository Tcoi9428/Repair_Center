from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Role, RoleRequest, AccessEvent

def require_manager(user):
    if not user.is_active or not user.has_perm('accounts.manage_access'):
        raise PermissionDenied

@transaction.atomic
def decide(request_id, actor, decision, comment):
    require_manager(actor)
    item = RoleRequest.objects.select_for_update().select_related('role').get(pk=request_id)
    if item.applicant_id == actor.pk:
        raise ValidationError('Свою заявку нельзя согласовать самостоятельно. Требуется другой администратор.')
    if item.status != 'pending':
        raise ValidationError('По этой заявке уже принято решение.')
    if decision not in ('approved','rejected') or (decision == 'rejected' and not comment.strip()):
        raise ValidationError('Укажите корректное решение и причину отклонения.')
    user = get_user_model().objects.select_for_update().get(pk=item.applicant_id)
    role = Role.objects.select_for_update().get(pk=item.role_id)
    if not user.is_active:
        raise ValidationError('Учетная запись заявителя неактивна.')
    if decision == 'approved':
        user.groups.add(role.group)
    item.status, item.review_comment = decision, comment
    item.reviewed_by, item.reviewed_at = actor, timezone.now()
    item.save()
    AccessEvent.objects.create(actor=actor, subject=user, role=role, action=decision, details={'request_id':item.pk,'comment':comment})

@transaction.atomic
def change_membership(actor, subject_id, role_id, action, reason):
    require_manager(actor)
    if actor.pk == subject_id:
        raise ValidationError('Собственные роли изменяет другой администратор.')
    if not reason.strip() or action not in ('grant','revoke'):
        raise ValidationError('Укажите действие и основание.')
    subject = get_user_model().objects.select_for_update().get(pk=subject_id)
    role = Role.objects.select_for_update().get(pk=role_id)
    if not subject.is_active:
        raise ValidationError('Учетная запись неактивна.')
    exists = subject.groups.filter(pk=role.group_id).exists()
    if exists == (action == 'grant'):
        raise ValidationError('Роль уже предоставлена.' if exists else 'У пользователя нет этой роли.')
    if action == 'grant':
        subject.groups.add(role.group)
    else:
        subject.groups.remove(role.group)
    AccessEvent.objects.create(actor=actor, subject=subject, role=role, action=action, details={'reason':reason})

@transaction.atomic
def save_role(form, actor):
    require_manager(actor)
    current = Role.objects.select_for_update().get(pk=form.instance.pk)
    if current.code == 'SYS_ADMIN':
        raise ValidationError('Системная роль администратора имеет фиксированные права.')
    if current.version != form.cleaned_data['expected_version']:
        raise ValidationError('Роль уже изменена. Обновите страницу.')
    before = list(current.group.permissions.values_list('codename',flat=True))
    previous = {'name':current.name,'scope':current.scope}
    current.name, current.scope = form.cleaned_data['name'], form.cleaned_data['scope']
    current.version += 1
    current.save()
    current.group.name = current.name
    current.group.save()
    current.group.permissions.set(form.cleaned_data['permissions'])
    AccessEvent.objects.create(actor=actor, role=current, action='role_updated', details={'before':before,'after':list(current.group.permissions.values_list('codename',flat=True)),'previous':previous,'name':current.name,'scope':current.scope})
