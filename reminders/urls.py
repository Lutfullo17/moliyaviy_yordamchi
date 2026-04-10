from django.urls import path
from . import views
app_name = 'reminders'

urlpatterns = [
    path('reminders/', views.reminder_list, name='list'),
    path('reminders/create/', views.reminder_create, name='create'),
]