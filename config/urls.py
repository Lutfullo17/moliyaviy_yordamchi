from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Root redirect
    path('', views.root_redirect, name='root-home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Ilovalar (Apps)
    path('users/', include('users.urls')),
    path('categories/', include('categories.urls')),
    path('transactions/', include('transactions.urls')),
    path('goals/', include('goals.urls')),
    path('planner/', include('planner.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)