from django.urls import path

from . import views


app_name = 'maintenance'

urlpatterns = [
    path('maintenance/cards/', views.card_list, name='card_list'),
    path('maintenance/cards/new/', views.card_edit, name='card_create'),
    path('maintenance/cards/<int:pk>/', views.card_detail, name='card_detail'),
    path('maintenance/cards/<int:pk>/edit/', views.card_edit, name='card_edit'),
    path('maintenance/equipment/<int:equipment_pk>/cards/', views.equipment_assignments, name='equipment_assignments'),
]
