from functools import reduce
from operator import or_
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .catalog import CATALOGS, BY_SLUG
from .forms import EquipmentDocumentFormSet
from .models import AuditEntry, Equipment, EquipmentModel, EquipmentStatus, EquipmentType, Company
from .services import save_record

COMPANY_DETAIL_FIELDS = (
    ('code', 'Код предприятия'),
    ('company_name_full', 'Наименование предприятия'),
    ('company_name_top_full', 'Основное предприятие'),
    ('company_name_short', 'Сокращенное наименование'),
    ('company_location', 'Город / населенный пункт'),
    ('service_contract', 'Договор на сервисное обслуживание'),
    ('service_contract_num', 'Номер сервисного договора'),
    ('company_contact', 'Контактный адрес'),
    ('company_ceo', 'ФИО руководителя'),
)

EQUIPMENT_FORM_TABS = (
    ('main', 'Основное', (
        'equipment_type', 'equipment_model', 'status', 'owner_company', 'operating_company',
        'factory_number', 'garage_number', 'commissioning_date', 'equipment_image',
    )),
    ('warranty', 'Условия гарантии', (
        'warranty_term_value', 'warranty_term_unit', 'warranty_extension_date',
        'warranty_extension_value', 'warranty_extension_unit',
    )),
    ('assemblies', 'Установленные узлы', (
        'engine_number', 'fire_suppression_system', 'remote_control_installed',
        'ccs_installed', 'ccs_name', 'control_system', 'hydraulic_cylinders',
    )),
    ('documents', 'Документы', (
        'supply_contract_number', 'sale_date', 'machine_kit_supply_contract', 'operation_manual',
    )),
)

def authorized_catalog(request, slug, action='view'):
    catalog = BY_SLUG.get(slug)
    if catalog is None:
        raise Http404
    if not request.user.has_perm(catalog.permission(action)):
        raise PermissionDenied
    return catalog

@login_required
def home(request):
    catalogs = [c for c in CATALOGS if request.user.has_perm(c.permission('view'))]
    if not catalogs:
        return render(request, 'directories/no_access.html', status=403)
    return render(request, 'directories/home.html', {'cards': [(c, c.model.objects.count()) for c in catalogs]})

@login_required
def catalog_list(request, slug):
    catalog = authorized_catalog(request, slug)
    queryset = catalog.model.objects.all()
    if catalog.model is EquipmentModel:
        queryset = queryset.select_related('equipment_type')
    elif catalog.model is Equipment:
        queryset = queryset.select_related('equipment_type', 'equipment_model', 'status', 'operating_company')
    query = request.GET.get('q', '').strip()[:200]
    if query:
        queryset = queryset.filter(reduce(or_, [Q(**{f'{field}__icontains': query}) for field in catalog.search_fields]))
    type_id = request.GET.get('type', '')
    if catalog.model is EquipmentModel and type_id.isdecimal():
        queryset = queryset.filter(equipment_type_id=type_id)
    if catalog.model is Equipment and type_id.isdecimal():
        queryset = queryset.filter(equipment_type_id=type_id)
    status_id = request.GET.get('status', '')
    if catalog.model is Equipment and status_id.isdecimal():
        queryset = queryset.filter(status_id=status_id)
    state = request.GET.get('state', '')
    if catalog.model is EquipmentStatus and state in ('active', 'inactive'):
        queryset = queryset.filter(is_active=state == 'active')
    if catalog.model is Company and state in ('yes', 'no'):
        queryset = queryset.filter(service_contract=state == 'yes')
    page = Paginator(queryset, 20).get_page(request.GET.get('page'))
    parameters = request.GET.copy()
    parameters.pop('page', None)
    return render(request, 'directories/list.html', {
        'catalog': catalog, 'page_obj': page, 'query': query, 'state': state, 'selected_type': type_id,
        'equipment_types': EquipmentType.objects.all() if catalog.model in (EquipmentModel, Equipment) else [],
        'equipment_statuses': EquipmentStatus.objects.filter(is_active=True) if catalog.model is Equipment else [],
        'selected_status': status_id,
        'can_add': request.user.has_perm(catalog.permission('add')),
        'can_change': request.user.has_perm(catalog.permission('change')),
        'page_query': parameters.urlencode(), 'total_count': catalog.model.objects.count(),
    })

@login_required
def record_detail(request, slug, pk):
    catalog = authorized_catalog(request, slug)
    queryset = catalog.model.objects.select_related('updated_by')
    if catalog.model is EquipmentModel:
        queryset = queryset.select_related('equipment_type')
    elif catalog.model is Equipment:
        queryset = queryset.select_related(
            'equipment_type', 'equipment_model', 'status', 'owner_company', 'operating_company', 'updated_by',
        ).prefetch_related(
            'other_documents',
            'technology_card_links__technology_card__maintenance_type',
        )
    record = get_object_or_404(queryset, pk=pk)
    history = AuditEntry.objects.filter(model_name=catalog.model._meta.model_name, object_id=pk).select_related('actor')[:10]
    if catalog.model is Equipment:
        return render(request, 'directories/equipment_detail.html', {
            'catalog': catalog,
            'record': record,
            'can_change': request.user.has_perm(catalog.permission('change')),
            'history': history,
            'technology_card_links': record.technology_card_links.select_related(
                'technology_card', 'technology_card__maintenance_type'
            ),
        })
    visual_kind = None
    if catalog.model is Company:
        visual_kind = 'company'
    elif catalog.model is EquipmentType and record.short_name.strip().upper() == 'ПДМ':
        visual_kind = 'pdm'
    elif catalog.model is EquipmentModel and record.equipment_type.short_name.strip().upper() == 'ПДМ':
        visual_kind = 'pdm'
    if catalog.model is Company:
        detail_fields = [{'name': name, 'label': label} for name, label in COMPANY_DETAIL_FIELDS]
    else:
        detail_fields = [
            {'name': name, 'label': 'Код' if name == 'id' else catalog.model._meta.get_field(name).verbose_name}
            for name in catalog.form.Meta.fields
        ]
    return render(request, 'directories/detail.html', {
        'catalog': catalog, 'record': record, 'detail_fields': detail_fields,
        'can_change': request.user.has_perm(catalog.permission('change')),
        'is_visual_card': catalog.model in (Company, EquipmentType, EquipmentModel), 'visual_kind': visual_kind,
        'history': history,
    })

@login_required
@require_http_methods(['GET', 'POST'])
def record_edit(request, slug, pk=None):
    catalog = authorized_catalog(request, slug, 'change' if pk else 'add')
    record = get_object_or_404(catalog.model, pk=pk) if pk else None
    if catalog.model is Equipment:
        form = catalog.form(request.POST or None, request.FILES or None, instance=record)
        formset = EquipmentDocumentFormSet(
            request.POST or None,
            request.FILES or None,
            instance=record or form.instance,
            prefix='documents',
        )
        if request.method == 'POST' and form.is_valid() and formset.is_valid():
            try:
                saved = save_record(form, request.user)
            except IntegrityError:
                form.add_error(None, 'Оборудование с таким идентификатором уже существует.')
            except ValidationError as exc:
                if hasattr(exc, 'message_dict'):
                    for key, errors in exc.message_dict.items():
                        for error in errors:
                            form.add_error(key if key in form.fields else None, error)
                else:
                    form.add_error(None, exc)
            else:
                formset.instance = saved
                formset.save()
                messages.success(request, 'Изменения сохранены.' if pk else 'Оборудование создано.')
                return redirect('directories:detail', slug=slug, pk=saved.pk)
        return render(request, 'directories/equipment_form.html', {
            'catalog': catalog,
            'form': form,
            'formset': formset,
            'record': record,
            'equipment_tabs': EQUIPMENT_FORM_TABS,
        })
    form = catalog.form(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        try:
            saved = save_record(form, request.user)
        except IntegrityError:
            form.add_error(None, 'Запись с таким кодом или наименованием уже существует. Проверьте данные.')
        except ValidationError as exc:
            if hasattr(exc, 'message_dict'):
                for key, errors in exc.message_dict.items():
                    for error in errors:
                        form.add_error(key if key in form.fields else None, error)
            else:
                form.add_error(None, exc)
        else:
            messages.success(request, 'Изменения сохранены.' if pk else 'Запись создана.')
            return redirect('directories:detail', slug=slug, pk=saved.pk)
    return render(request, 'directories/form.html', {'catalog': catalog, 'form': form, 'record': record})
