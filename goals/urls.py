from django.urls import path
from . import views

app_name = 'goals'

urlpatterns = [
    path('', views.goal_list, name='list'),
    path('create/', views.goal_create, name='create'),
    path('<int:pk>/update/', views.goal_update, name='update'),
    path('<int:pk>/delete/', views.goal_delete, name='delete'),
    path('<int:pk>/ai_recommendation/', views.ai_recommend_view, name='ai_recommendation'),
]