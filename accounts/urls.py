from django.urls import path
from . import views
app_name = 'accounts'
urlpatterns = [
    path('workspace/',views.workspace,name='workspace'),
    path('access/requests/',views.requests_page,name='requests'),
    path('access/roles/',views.roles_page,name='roles'),
    path('access/roles/<int:pk>/edit/',views.role_edit,name='role_edit'),
    path('access/approvals/',views.queue,name='queue'),
    path('access/approvals/<int:pk>/',views.review,name='review'),
    path('access/users/',views.users,name='users'),
    path('access/users/new/',views.new_user,name='new_user'),
    path('access/users/<int:pk>/',views.user_roles,name='user_roles'),
    path('access/audit/',views.audit,name='audit'),
]
