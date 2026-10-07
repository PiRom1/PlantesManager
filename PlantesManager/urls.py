"""
URL configuration for PlantesManager project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('Plantes.urls')),
    path('admin/', admin.site.urls),
]
