from django.contrib import admin

from .models import (
    EquipmentOperatingHours,
    EquipmentTechnologyCard,
    TechnologyCard,
    TechnologyCardMaterial,
    TechnologyCardOperation,
)


class OperationInline(admin.TabularInline):
    model = TechnologyCardOperation
    extra = 0


class MaterialInline(admin.TabularInline):
    model = TechnologyCardMaterial
    extra = 0


@admin.register(TechnologyCard)
class TechnologyCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'equipment_model', 'maintenance_type', 'revision', 'status', 'updated_at']
    list_filter = ['status', 'equipment_model', 'maintenance_type']
    search_fields = ['name', 'equipment_model__name', 'maintenance_type__name']
    inlines = [OperationInline, MaterialInline]


@admin.register(EquipmentTechnologyCard)
class EquipmentTechnologyCardAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'technology_card', 'assigned_at', 'assigned_by']
    search_fields = ['equipment__equipment_identifier', 'technology_card__name']


@admin.register(EquipmentOperatingHours)
class EquipmentOperatingHoursAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'measured_at', 'operating_hours', 'updated_by']
    list_filter = ['measured_at', 'equipment__equipment_model']
    search_fields = ['equipment__equipment_identifier', 'equipment__garage_number']
    readonly_fields = ['created_at', 'updated_at', 'updated_by', 'version']
