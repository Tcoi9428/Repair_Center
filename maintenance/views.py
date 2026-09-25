from functools import reduce
from operator import or_

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from directories.models import AuditEntry, Equipment, EquipmentModel

from .forms import (
    EquipmentTechnologyCardForm,
    EquipmentOperatingHoursForm,
    TechnologyCardForm,
    TechnologyCardMaterialFormSet,
    TechnologyCardOperationFormSet,
)
from .models import EquipmentOperatingHours, MaintenanceType, TechnologyCard
from directories.services import save_record
from .services import grouped_operations, save_equipment_assignments, save_technology_card


def require_card_permission(user, action='view'):
    if not user.has_perm(f'maintenance.{action}_technologycard'):
        raise PermissionDenied


@login_required
def card_list(request):
    require_card_permission(request.user)
    queryset = TechnologyCard.objects.select_related('equipment_model', 'maintenance_type', 'updated_by')
    query = request.GET.get('q', '').strip()[:200]
    if query:
        queryset = queryset.filter(
            reduce(
                or_,
                [
                    Q(name__icontains=query),
                    Q(equipment_model__name__icontains=query),
                    Q(maintenance_type__name__icontains=query),
                ],
            )
        )
    model_id = request.GET.get('model', '')
    if model_id.isdecimal():
        queryset = queryset.filter(equipment_model_id=model_id)
    type_id = request.GET.get('type', '')
    if type_id.isdecimal():
        queryset = queryset.filter(maintenance_type_id=type_id)
    status = request.GET.get('status', '')
    if status in TechnologyCard.Status.values:
        queryset = queryset.filter(status=status)
    page = Paginator(queryset, 20).get_page(request.GET.get('page'))
    parameters = request.GET.copy()
    parameters.pop('page', None)
    return render(
        request,
        'maintenance/card_list.html',
        {
            'page_obj': page,
            'query': query,
            'selected_model': model_id,
            'selected_type': type_id,
            'selected_status': status,
            'equipment_models': EquipmentModel.objects.select_related('equipment_type'),
            'maintenance_types': MaintenanceType.objects.filter(is_active=True),
            'status_choices': TechnologyCard.Status.choices,
            'can_add': request.user.has_perm('maintenance.add_technologycard'),
            'page_query': parameters.urlencode(),
            'total_count': TechnologyCard.objects.count(),
            'maintenance_section': True,
        },
    )


@login_required
def card_detail(request, pk):
    require_card_permission(request.user)
    card = get_object_or_404(
        TechnologyCard.objects.select_related(
            'equipment_model', 'equipment_model__equipment_type', 'maintenance_type', 'updated_by'
        ).prefetch_related('operations', 'required_materials__material', 'equipment_links__equipment'),
        pk=pk,
    )
    history = AuditEntry.objects.filter(model_name='technologycard', object_id=pk).select_related('actor')[:10]
    return render(
        request,
        'maintenance/card_detail.html',
        {
            'card': card,
            'operation_groups': grouped_operations(card),
            'part_materials': card.required_materials.filter(kind='part').select_related('material'),
            'lubricants': card.required_materials.filter(kind='lubricant').select_related('material'),
            'can_change': request.user.has_perm('maintenance.change_technologycard'),
            'history': history,
            'maintenance_section': True,
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def card_edit(request, pk=None):
    require_card_permission(request.user, 'change' if pk else 'add')
    card = get_object_or_404(TechnologyCard, pk=pk) if pk else TechnologyCard()
    form = TechnologyCardForm(request.POST or None, instance=card)
    operation_formset = TechnologyCardOperationFormSet(
        request.POST or None,
        instance=card,
        prefix='operations',
    )
    material_formset = TechnologyCardMaterialFormSet(
        request.POST or None,
        instance=card,
        prefix='materials',
    )
    if request.method == 'POST' and form.is_valid() and operation_formset.is_valid() and material_formset.is_valid():
        try:
            saved = save_technology_card(form, operation_formset, material_formset, request.user)
        except (IntegrityError, ValidationError) as exc:
            form.add_error(None, getattr(exc, 'message', str(exc)))
        else:
            messages.success(request, 'Технологическая карта сохранена.')
            return redirect('maintenance:card_detail', pk=saved.pk)
    return render(
        request,
        'maintenance/card_form.html',
        {
            'form': form,
            'operation_formset': operation_formset,
            'material_formset': material_formset,
            'card': card if card.pk else None,
            'maintenance_section': True,
        },
    )


@login_required
@require_http_methods(['GET', 'POST'])
def equipment_assignments(request, equipment_pk):
    if not request.user.has_perm('directories.change_equipment'):
        raise PermissionDenied
    require_card_permission(request.user)
    equipment = get_object_or_404(
        Equipment.objects.select_related('equipment_model', 'equipment_type'),
        pk=equipment_pk,
    )
    form = EquipmentTechnologyCardForm(request.POST or None, equipment=equipment)
    if request.method == 'POST' and form.is_valid():
        save_equipment_assignments(equipment, form.cleaned_data['technology_cards'], request.user)
        messages.success(request, 'Привязки технологических карт обновлены.')
        return redirect('directories:detail', slug='equipment', pk=equipment.pk)
    return render(
        request,
        'maintenance/equipment_assignments.html',
        {'form': form, 'equipment': equipment, 'maintenance_section': True},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def operating_hours_edit(request, equipment_pk=None, pk=None):
    action = 'change' if pk else 'add'
    if not request.user.has_perm(f'maintenance.{action}_equipmentoperatinghours'):
        raise PermissionDenied
    if pk:
        reading = get_object_or_404(
            EquipmentOperatingHours.objects.select_related('equipment', 'equipment__equipment_model'),
            pk=pk,
        )
        equipment = reading.equipment
    else:
        equipment = get_object_or_404(
            Equipment.objects.select_related('equipment_model'),
            pk=equipment_pk,
        )
        reading = EquipmentOperatingHours(equipment=equipment, measured_at=timezone.now())
    form = EquipmentOperatingHoursForm(request.POST or None, instance=reading)
    if request.method == 'POST' and form.is_valid():
        try:
            saved = save_record(form, request.user)
        except IntegrityError:
            form.add_error('measured_at', 'Для этой даты и времени показание уже зарегистрировано.')
        except ValidationError as exc:
            if hasattr(exc, 'message_dict'):
                for field, errors in exc.message_dict.items():
                    for error in errors:
                        form.add_error(field if field in form.fields else None, error)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, 'Показание наработки сохранено.')
            return redirect(f'{reverse("directories:detail", args=["equipment", saved.equipment_id])}#operating-hours')
    return render(request, 'maintenance/operating_hours_form.html', {
        'form': form,
        'equipment': equipment,
        'reading': reading if reading.pk else None,
        'equipment_section': True,
    })
