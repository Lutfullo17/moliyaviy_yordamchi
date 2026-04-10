# planner/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Bu yerda bo'sh joy bo'lishi kerak, 'planner/' emas!
    path('', views.daily_plan, name='daily-plan'),
    path('today/', views.today_plan_view, name='today-plan'),
    path('<int:plan_id>/task/create/', views.task_create, name='task-create'),
    path('task/<int:task_id>/update/', views.task_update, name='task-update'),
    path('task/<int:task_id>/delete/', views.task_delete, name='task-delete'),
    path('task/<int:task_id>/status/', views.task_update_status, name='task-status'),
    path('api/upcoming-tasks/', views.upcoming_tasks_api, name='api-upcoming-tasks'),
]