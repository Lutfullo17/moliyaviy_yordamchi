from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_list, name='list'),
    path('create/', views.transaction_create, name='create'),
    path('<int:pk>/update/', views.transaction_update, name='update'),
    path('<int:pk>/delete/', views.transaction_delete, name='delete'),
    path('summary/', views.transaction_summary, name='summary'),
]