"""
Peuple la table PlantState avec les états physiologiques de base.

Usage :
    python manage.py runscript populate_plant_states

Idempotent : relancer le script met à jour les entrées existantes (clé = code)
sans créer de doublon.
"""

from django.db import transaction

from Plantes.models import PlantState


PLANT_STATES = [
    {'code': 'CUTTING', 'name': 'Bouture',
     'description': "Fragment prélevé sur une plante mère, en cours d'enracinement."},
    {'code': 'SEEDLING', 'name': 'Jeune pousse',
     'description': 'Plante récemment enracinée, encore fragile.'},
    {'code': 'GROWTH', 'name': 'Croissance',
     'description': 'Période active : la plante développe feuilles et racines.'},
    {'code': 'FLOWERING', 'name': 'Floraison',
     'description': 'La plante produit des fleurs.'},
    {'code': 'FRUITING', 'name': 'Fructification',
     'description': 'La plante développe ses fruits ou ses graines.'},
    {'code': 'DORMANCY', 'name': 'Dormance',
     'description': 'Repos végétatif : croissance arrêtée, besoins en eau réduits.'},
    {'code': 'WATER_STRESS', 'name': 'Stress hydrique',
     'description': "Manque ou excès d'eau : feuilles molles, jaunissement."},
    {'code': 'RECOVERY', 'name': 'Convalescence',
     'description': "Plante en cours de récupération après un stress, une maladie ou un rempotage."},
    {'code': 'DEAD', 'name': 'Morte',
     'description': 'La plante n\'a pas survécu.'},
]


def run():
    created = updated = 0

    with transaction.atomic():
        for row in PLANT_STATES:
            defaults = {key: value for key, value in row.items() if key != 'code'}
            _, was_created = PlantState.objects.update_or_create(code=row['code'], defaults=defaults)

            if was_created:
                created += 1
            else:
                updated += 1

    print(f'PlantState        {created:>3} créé(s), {updated:>3} mis à jour')
