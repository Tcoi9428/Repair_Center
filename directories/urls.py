from django.urls import path
from . import views
app_name = 'directories'
urlpatterns = [
    path('nsi/', views.home, name='home'),
    path('nsi/<slug:slug>/', views.catalog_list, name='list'),
    path('nsi/<slug:slug>/new/', views.record_edit, name='create'),
    path('nsi/<slug:slug>/<int:pk>/', views.record_detail, name='detail'),
    path('nsi/<slug:slug>/<int:pk>/edit/', views.record_edit, name='edit'),
]
