from django.urls import path
from . import views

app_name = 'reminders'

urlpatterns = [
    path('', views.reminder_list, name='list'),
    path('create/', views.reminder_create, name='create'),
    path('<int:pk>/toggle/', views.reminder_toggle, name='toggle'),
    path('<int:pk>/delete/', views.reminder_delete, name='delete'),
]
