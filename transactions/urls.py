from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_list, name='list'),
    path('create/', views.transaction_create, name='create'),
    path('<int:pk>/update/', views.transaction_update, name='update'),
    path('<int:pk>/delete/', views.transaction_delete, name='delete'),
    path('summary/', views.transaction_summary, name='summary'),
    path('export/csv/', views.transaction_export_csv, name='export_csv'),
    path('api/category-breakdown/', views.category_breakdown_api, name='api_category_breakdown'),
    path('api/voice-parse/', views.voice_parse, name='api_voice_parse'),
    path('api/voice-create/', views.voice_create, name='api_voice_create'),
]
