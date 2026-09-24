from django.contrib import admin
from django.core.exceptions import ValidationError
from .catalog import CATALOGS
from .models import AuditEntry, EquipmentDocument
from .services import record_change, snapshot

class ReferenceAdmin(admin.ModelAdmin):
    readonly_fields = ['id', 'created_at', 'updated_at', 'updated_by', 'version']
    save_on_top = True

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, change=False, **kwargs):
        base = super().get_form(request, obj, change=change, **kwargs)

        class LockedAdminForm(base):
            def clean(self):
                data = super().clean()
                if self.instance.pk:
                    current = type(self.instance).objects.select_for_update().get(pk=self.instance.pk)
                    if data.get('expected_version') != current.version:
                        raise ValidationError('Запись уже изменена. Обновите страницу и повторите изменения.')
                return data

        return LockedAdminForm

    def save_model(self, request, obj, form, change):
        # Django admin wraps a change form in a transaction. A row lock also
        # prevents an admin edit from silently replacing a concurrent web edit.
        before = {}
        if change:
            current = type(obj).objects.select_for_update().get(pk=obj.pk)
            before = snapshot(current)
            obj.version = current.version + 1
        obj.updated_by = request.user
        obj.save()
        record_change(obj, request.user, before, 'update' if change else 'create')

for catalog in CATALOGS:
    if catalog.slug == 'equipment':
        list_filter = ('equipment_type', 'status', 'operating_company')
    elif catalog.slug == 'equipment-models':
        list_filter = ('equipment_type',)
    elif catalog.slug == 'equipment-statuses':
        list_filter = ('is_active',)
    else:
        list_filter = ()
    klass = type(f'{catalog.model.__name__}Admin', (ReferenceAdmin,), {
        'form': catalog.form, 'list_display': catalog.columns, 'search_fields': catalog.search_fields,
        'list_filter': list_filter,
    })
    admin.site.register(catalog.model, klass)

@admin.register(EquipmentDocument)
class EquipmentDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'equipment', 'uploaded_at']
    search_fields = ['title', 'equipment__equipment_identifier']
    list_filter = ['uploaded_at']

@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'actor', 'model_name', 'object_label', 'action']
    list_filter = ['model_name', 'action']
    search_fields = ['object_label', 'actor__username']
    readonly_fields = ['created_at', 'actor', 'model_name', 'object_id', 'object_label', 'action', 'before', 'after']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
