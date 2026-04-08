from django.urls import path
from . import views

urlpatterns = [
    path('planner/today/', views.TodayPlanView.as_view(), name='today-plan'),
    path('planner/', views.PlanByDateView.as_view(), name='plan-by-date'),
    path('tasks/', views.TaskListCreateView.as_view(), name='task-create'),
    path('tasks/<int:task_id>/', views.TaskDetailView.as_view(), name='task-detail'),
]