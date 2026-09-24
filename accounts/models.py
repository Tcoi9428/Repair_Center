from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Q

class Role(models.Model):
    code = models.SlugField('Шифр', max_length=40, unique=True)
    name = models.CharField('Название', max_length=150, unique=True)
    scope = models.TextField('Назначение и область действия')
    group = models.OneToOneField(Group, on_delete=models.PROTECT, related_name='system_role')
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']
        permissions = [('manage_access', 'Управление ролями, пользователями и согласование заявок')]
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return f'{self.code} · {self.name}'

class RoleRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'На согласовании'
        APPROVED = 'approved', 'Согласована'
        REJECTED = 'rejected', 'Отклонена'
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='role_requests')
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    reason = models.TextField('Обоснование', max_length=2000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='reviewed_role_requests')
    review_comment = models.TextField(blank=True, max_length=2000)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['applicant', 'role'], condition=Q(status='pending'), name='one_pending_role_request')]

class AccessEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    subject = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name='+')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=40, choices=[('requested','Подана заявка'),('approved','Заявка согласована'),('rejected','Заявка отклонена'),('grant','Роль предоставлена'),('revoke','Роль отозвана'),('role_updated','Права роли изменены'),('user_created','Пользователь создан')])
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
