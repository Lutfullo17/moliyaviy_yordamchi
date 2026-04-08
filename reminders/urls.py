from django.urls import path
from . import views

urlpatterns = [
    path('reminders/', views.ReminderListCreateView.as_view(), name='reminder-list'),
    path('reminders/<int:reminder_id>/', views.ReminderDetailView.as_view(), name='reminder-detail'),
]