from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from accounts.views import public_home

admin.site.site_header = 'Ремонтный Центр · администрирование'
admin.site.site_title = 'Ремонтный Центр'
admin.site.index_title = 'Пользователи и справочники'

urlpatterns = [
    path('', public_home, name='public_home'),
    path('', include('accounts.urls')),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('directories.urls')),
    path('', include('maintenance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
