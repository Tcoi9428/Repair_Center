from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import Role, RoleRequest, AccessEvent
from .forms import RequestForm, DecisionForm, RoleForm, NewUserForm, MembershipForm
from .services import require_manager, decide, save_role, change_membership

def public_home(request):
    return render(request, 'public.html')

@login_required
def workspace(request):
    return render(request, 'accounts/workspace.html', {'roles':Role.objects.filter(group__in=request.user.groups.all()).prefetch_related('group__permissions__content_type')})

@login_required
@require_http_methods(['GET','POST'])
def requests_page(request):
    form = RequestForm(request.POST if request.method == 'POST' else None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                item = form.save(commit=False)
                item.applicant = request.user
                item.save()
                AccessEvent.objects.create(actor=request.user,subject=request.user,role=item.role,action='requested',details={'request_id':item.pk})
        except IntegrityError:
            form.add_error(None,'Заявка на эту роль уже находится на согласовании.')
        else:
            messages.success(request,'Заявка направлена администратору системы.')
            return redirect('accounts:requests')
    items = request.user.role_requests.select_related('role','reviewed_by')
    return render(request,'accounts/requests.html',{'form':form,'page_obj':Paginator(items,20).get_page(request.GET.get('page'))})

@login_required
def roles_page(request):
    return render(request,'accounts/roles.html',{'roles':Role.objects.prefetch_related('group__permissions__content_type')})

@login_required
@require_http_methods(['GET','POST'])
def role_edit(request, pk):
    require_manager(request.user)
    role = get_object_or_404(Role,pk=pk)
    if role.code == 'SYS_ADMIN':
        messages.info(request,'Права системного администратора фиксированы.')
        return redirect('accounts:roles')
    form = RoleForm(request.POST if request.method == 'POST' else None,instance=role)
    if request.method == 'POST' and form.is_valid():
        try:
            save_role(form,request.user)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None,exc if isinstance(exc,ValidationError) else 'Название уже используется другой группой или ролью.')
        else:
            messages.success(request,'Роль сохранена. Права применены ко всем ее пользователям.')
            return redirect('accounts:roles')
    return render(request,'accounts/form.html',{'form':form,'title':f'Роль {role.code}','subtitle':'Изменение прав действует для всех пользователей этой роли. Шифр постоянный.'})

@login_required
def queue(request):
    require_manager(request.user)
    status = request.GET.get('status','pending')
    if status not in ('pending','approved','rejected','all'):
        status = 'pending'
    items = RoleRequest.objects.select_related('role','applicant','reviewed_by')
    if status != 'all':
        items = items.filter(status=status)
    return render(request,'accounts/queue.html',{'page_obj':Paginator(items,20).get_page(request.GET.get('page')),'status':status})

@login_required
@require_http_methods(['GET','POST'])
def review(request,pk):
    require_manager(request.user)
    item = get_object_or_404(RoleRequest.objects.select_related('role','applicant','reviewed_by'),pk=pk)
    form = DecisionForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            decide(item.pk,request.user,form.cleaned_data['decision'],form.cleaned_data['comment'])
        except ValidationError as exc:
            form.add_error(None,exc)
        else:
            messages.success(request,'Решение сохранено.')
            return redirect('accounts:review',pk=pk)
    return render(request,'accounts/review.html',{'item':item,'form':form})

@login_required
def users(request):
    require_manager(request.user)
    items = get_user_model().objects.order_by('username').prefetch_related('groups__system_role')
    q = request.GET.get('q','').strip()[:150]
    if q:
        from django.db.models import Q
        items = items.filter(Q(username__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q))
    return render(request,'accounts/users.html',{'page_obj':Paginator(items,20).get_page(request.GET.get('page')),'q':q})

@login_required
@require_http_methods(['GET','POST'])
def new_user(request):
    require_manager(request.user)
    form = NewUserForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            subject = form.save()
            AccessEvent.objects.create(actor=request.user,subject=subject,action='user_created')
        messages.success(request,'Учетная запись создана без ролей. Пользователь может войти и подать заявку.')
        return redirect('accounts:user_roles',pk=subject.pk)
    return render(request,'accounts/form.html',{'form':form,'title':'Создать пользователя','subtitle':'Новая учетная запись не получает доступ к справочникам до предоставления роли.'})

@login_required
@require_http_methods(['GET','POST'])
def user_roles(request,pk):
    require_manager(request.user)
    subject = get_object_or_404(get_user_model(),pk=pk)
    form = MembershipForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            change_membership(request.user,pk,form.cleaned_data['role'].pk,form.cleaned_data['action'],form.cleaned_data['reason'])
        except ValidationError as exc:
            form.add_error(None,exc)
        else:
            messages.success(request,'Состав ролей обновлен.')
            return redirect('accounts:user_roles',pk=pk)
    return render(request,'accounts/user_roles.html',{'subject':subject,'form':form,'roles':Role.objects.filter(group__in=subject.groups.all()),'events':AccessEvent.objects.filter(subject=subject).select_related('actor','role')[:30]})

@login_required
def audit(request):
    require_manager(request.user)
    return render(request,'accounts/audit.html',{'page_obj':Paginator(AccessEvent.objects.select_related('actor','subject','role'),30).get_page(request.GET.get('page'))})
