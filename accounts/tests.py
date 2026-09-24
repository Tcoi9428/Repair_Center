from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from .models import Role, RoleRequest, AccessEvent
from .services import decide, change_membership

class AccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.worker = User.objects.create_user('worker',password='Good-local-test-845!')
        cls.other = User.objects.create_user('other')
        cls.manager = User.objects.create_user('manager')
        cls.manager.groups.add(Role.objects.get(code='SYS_ADMIN').group)
        cls.nsi = Role.objects.get(code='NSI')
        cls.planner = Role.objects.get(code='PLAN_SPEC')

    def setUp(self):
        self.client.force_login(self.worker)

    def test_public_home_no_redirect_no_private_data_and_separate_login(self):
        client = Client()
        response = client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Войти в систему')
        self.assertNotContains(response,'name="password"')
        self.assertNotContains(response,'worker')
        self.assertEqual(client.get('/workspace/').status_code,302)
        self.assertContains(client.get('/login/'),'name="password"')
        self.assertContains(self.client.get('/workspace/'),'Роли пока не назначены')
        self.assertEqual(self.client.get('/login/').status_code,302)

    def test_seeded_roles_and_existing_nsi_membership(self):
        self.assertEqual(Role.objects.count(),9)
        self.worker.groups.add(self.nsi.group)
        self.assertContains(self.client.get('/workspace/'),'Специалист НСИ')
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,200)

    def test_request_grants_nothing_until_approval_and_supports_multiple_roles(self):
        self.worker.groups.add(self.planner.group)
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,403)
        response = self.client.post('/access/requests/',{'role':self.nsi.pk,'reason':'Ведение нормативов'})
        self.assertEqual(response.status_code,302)
        item = RoleRequest.objects.get()
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,403)
        self.client.force_login(self.manager)
        self.assertFalse(self.manager.is_superuser)
        self.assertEqual(self.client.post(reverse('accounts:review',args=[item.pk]),{'decision':'approved','comment':'Разрешено'}).status_code,302)
        self.client.force_login(self.worker)
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,200)
        self.assertEqual(self.worker.groups.count(),2)
        item.refresh_from_db()
        self.assertEqual(item.reviewed_by,self.manager)
        self.assertIsNotNone(item.reviewed_at)

    def test_duplicate_pending_and_assigned_role_requests_blocked(self):
        self.client.post('/access/requests/',{'role':self.nsi.pk,'reason':'Данные'})
        self.assertEqual(self.client.post('/access/requests/',{'role':self.nsi.pk,'reason':'Повтор'}).status_code,200)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RoleRequest.objects.create(applicant=self.worker,role=self.nsi,reason='race')
        self.worker.groups.add(self.planner.group)
        self.assertEqual(self.client.post('/access/requests/',{'role':self.planner.pk,'reason':'Повтор'}).status_code,200)
        self.assertEqual(RoleRequest.objects.count(),1)

    def test_rejection_requires_comment_allows_resubmit_and_no_repeat_decision(self):
        item = RoleRequest.objects.create(applicant=self.worker,role=self.nsi,reason='Ведение')
        self.client.force_login(self.manager)
        url = reverse('accounts:review',args=[item.pk])
        self.assertContains(self.client.post(url,{'decision':'rejected','comment':''}),'Укажите причину')
        decide(item.pk,self.manager,'rejected','Не входит в обязанности')
        with self.assertRaises(ValidationError): decide(item.pk,self.manager,'approved','')
        self.assertFalse(self.worker.groups.filter(pk=self.nsi.group_id).exists())
        self.client.force_login(self.worker)
        self.assertEqual(self.client.post('/access/requests/',{'role':self.nsi.pk,'reason':'Новая задача'}).status_code,302)

    def test_no_self_approval_no_inactive_user_approval(self):
        item = RoleRequest.objects.create(applicant=self.manager,role=self.nsi,reason='Себе')
        with self.assertRaises(ValidationError): decide(item.pk,self.manager,'approved','')
        self.worker.is_active=False
        self.worker.save()
        item = RoleRequest.objects.create(applicant=self.worker,role=self.nsi,reason='Запрос')
        with self.assertRaises(ValidationError): decide(item.pk,self.manager,'approved','')

    def test_admin_routes_and_foreign_requests_forbidden_for_ordinary_user(self):
        item = RoleRequest.objects.create(applicant=self.other,role=self.nsi,reason='Private request text')
        for url in ['/access/approvals/','/access/users/','/access/users/new/','/access/audit/',reverse('accounts:review',args=[item.pk]),reverse('accounts:role_edit',args=[self.nsi.pk]),reverse('accounts:user_roles',args=[self.other.pk])]:
            self.assertEqual(self.client.get(url).status_code,403,url)
            self.assertEqual(self.client.post(url,{'decision':'approved'}).status_code,403,url)
        self.assertNotContains(self.client.get('/access/requests/'),'Private request text')

    def test_grant_revoke_audited_no_self_change(self):
        change_membership(self.manager,self.worker.pk,self.nsi.pk,'grant','Новая задача')
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,200)
        change_membership(self.manager,self.worker.pk,self.nsi.pk,'revoke','Задача завершена')
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,403)
        self.assertEqual(AccessEvent.objects.filter(subject=self.worker).count(),2)
        with self.assertRaises(ValidationError): change_membership(self.manager,self.manager.pk,self.nsi.pk,'grant','Себе')

    def test_role_permissions_edit_applies_to_members_no_privilege_injection_or_stale_save(self):
        self.worker.groups.add(self.planner.group)
        self.client.force_login(self.manager)
        url = reverse('accounts:role_edit',args=[self.planner.pk])
        view = Permission.objects.get(codename='view_company')
        add = Permission.objects.get(codename='add_company')
        forbidden = Permission.objects.get(codename='manage_access')
        data={'name':self.planner.name,'scope':'Просмотр предприятий','expected_version':1,'permissions':[view.pk,forbidden.pk]}
        self.assertEqual(self.client.post(url,data).status_code,200)
        data['permissions']=[add.pk]
        self.assertContains(self.client.post(url,data),'нужно также разрешить просмотр')
        data['permissions']=[view.pk,add.pk]
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertContains(self.client.post(url,data),'Роль уже изменена')
        self.client.force_login(self.worker)
        self.assertEqual(self.client.get('/nsi/companies/new/').status_code,200)
        self.assertEqual(self.client.get('/nsi/equipment-types/').status_code,403)
        self.assertEqual(self.client.get('/access/users/').status_code,403)

    def test_manager_pages_render_and_create_user_without_privileges(self):
        self.client.force_login(self.manager)
        for url in ['/workspace/','/access/roles/','/access/requests/','/access/approvals/','/access/users/','/access/users/new/','/access/audit/',reverse('accounts:user_roles',args=[self.worker.pk]),reverse('accounts:role_edit',args=[self.nsi.pk])]:
            self.assertEqual(self.client.get(url).status_code,200,url)
        response=self.client.post('/access/users/new/',{'username':'newmember','password1':'Good-test-password-842!','password2':'Good-test-password-842!','is_superuser':'on'})
        self.assertEqual(response.status_code,302)
        user=get_user_model().objects.get(username='newmember')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.groups.count(),0)

    def test_csrf_required_for_request_and_decision(self):
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.worker)
        self.assertEqual(client.post('/access/requests/',{'role':self.nsi.pk,'reason':'CSRF'}).status_code,403)
        item=RoleRequest.objects.create(applicant=self.worker,role=self.nsi,reason='Запрос')
        client.force_login(self.manager)
        self.assertEqual(client.post(reverse('accounts:review',args=[item.pk]),{'decision':'approved'}).status_code,403)
