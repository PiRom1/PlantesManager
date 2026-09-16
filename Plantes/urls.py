from django.urls import path, include
from Plantes.views import plant_views, pot_views, species_views, spot_views

urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),

    # Species
    path('species/', species_views.list_species, name='list_species'),
    path('specie/<int:id_specie>/', species_views.detail_specie, name='detail_specie'),
    path('api/species/search/', species_views.search_species, name='search_species'),

    # Plants
    path('plants/', plant_views.list_plants, name='list_plants'),
    path('plant/add/', plant_views.add_plant, name='add_plant'),
    path('plant/<int:id_plant>/', plant_views.detail_plant, name='detail_plant'),
    path('plant/<int:id_plant>/edit/', plant_views.edit_plant, name='edit_plant'),

    # Spots
    path('spots/', spot_views.list_spots, name='list_spots'),
    path('spot/add/', spot_views.add_spot, name='add_spot'),
    path('spot/<int:id_spot>/', spot_views.detail_spot, name='detail_spot'),

    # Pots
    path('pots/', pot_views.list_pots, name='list_pots'),
    path('pot/add/', pot_views.add_pot, name='add_pot'),
    path('pot/<int:id_pot>/', pot_views.detail_pot, name='detail_pot'),
]
