from django.urls import path, include
from Plantes.views import species_views

urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),

    # Species
    path('species/', species_views.list_species, name='list_species'),
    path('specie/<int:id_specie>/', species_views.detail_specie, name='detail_specie'),
]
