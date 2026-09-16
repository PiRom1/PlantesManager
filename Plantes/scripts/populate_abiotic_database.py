"""
Peuple la base avec les référentiels abiotiques de base.

Usage :
    python manage.py runscript populate_abiotic_database

Idempotent : relancer le script met à jour les entrées existantes (clé = code)
sans créer de doublon. Les espèces (Specie) ne sont pas gérées ici.

Pour ajouter ou modifier une entrée, éditer simplement les listes ci-dessous :
les clés des dictionnaires sont les noms des champs du modèle.
"""

from django.db import transaction

from Plantes.models import (
    Action,
    DroughtTolerance,
    Exposure,
    Humidity,
    Substrate,
)


ACTIONS = [
    {'code': 'WATER', 'name': 'Arrosage', 'description': "Apporter de l'eau au substrat."},
    {'code': 'MIST', 'name': 'Brumisation', 'description': "Vaporiser de l'eau sur le feuillage pour augmenter l'hygrométrie."},
    {'code': 'FERTILIZE', 'name': 'Fertilisation', 'description': "Apporter de l'engrais."},
    {'code': 'PRUNE', 'name': 'Taille', 'description': 'Couper les tiges ou feuilles mortes, abîmées ou en excès.'},
    {'code': 'REPOT', 'name': 'Rempotage', 'description': 'Changer la plante de pot, généralement pour un plus grand.'},
    {'code': 'CHANGE_SUBSTRATE', 'name': 'Changement de substrat', 'description': 'Renouveler le substrat sans forcément changer de pot.'},
    {'code': 'MOVE', 'name': 'Déplacement', 'description': "Changer la plante d'emplacement."},
    {'code': 'CLEAN_LEAVES', 'name': 'Nettoyage du feuillage', 'description': 'Dépoussiérer les feuilles pour préserver la photosynthèse.'},
    {'code': 'CHECK_PESTS', 'name': 'Inspection parasites', 'description': 'Vérifier la présence de nuisibles ou de maladies.'},
    {'code': 'ROTATE', 'name': 'Rotation', 'description': 'Tourner le pot pour équilibrer la croissance vers la lumière.'},
    {'code': 'PROPAGATE', 'name': 'Bouturage', 'description': 'Prélever une bouture pour multiplier la plante.'},
]


# drying_factor : 1.0 = terreau universel de référence. > 1 sèche plus vite.
SUBSTRATES = [
    {'code': 'UNIVERSAL', 'name': 'Terreau universel', 'drying_factor': 1.0, 'renew_months': 24,
     'description': 'Terreau polyvalent, référence de séchage.'},
    {'code': 'GREEN_PLANTS', 'name': 'Terreau plantes vertes', 'drying_factor': 0.95, 'renew_months': 24,
     'description': 'Terreau enrichi, rétention en eau légèrement supérieure.'},
    {'code': 'AERATED_MIX', 'name': 'Terreau aéré (perlite)', 'drying_factor': 1.2, 'renew_months': 24,
     'description': 'Terreau allégé de perlite ou vermiculite, meilleur drainage.'},
    {'code': 'CACTUS', 'name': 'Terreau cactus et succulentes', 'drying_factor': 1.4, 'renew_months': 36,
     'description': 'Mélange sableux très drainant.'},
    {'code': 'SEEDLING', 'name': 'Terreau de semis', 'drying_factor': 1.1, 'renew_months': 12,
     'description': 'Substrat fin et pauvre, destiné aux jeunes pousses.'},
    {'code': 'ORCHID_BARK', 'name': 'Écorces pour orchidées', 'drying_factor': 1.8, 'renew_months': 24,
     'description': 'Écorces de pin, substrat très aéré et drainant.'},
    {'code': 'SPHAGNUM', 'name': 'Sphaigne', 'drying_factor': 0.7, 'renew_months': 12,
     'description': 'Mousse très rétentrice en eau.'},
    {'code': 'COCO_COIR', 'name': 'Fibre de coco', 'drying_factor': 0.9, 'renew_months': 24,
     'description': 'Fibre de coco, bonne rétention et aération.'},
    {'code': 'HEATH_SOIL', 'name': 'Terre de bruyère', 'drying_factor': 0.9, 'renew_months': 24,
     'description': 'Substrat acide pour plantes acidophiles.'},
    {'code': 'LECA', 'name': "Billes d'argile (semi-hydro)", 'drying_factor': 2.0, 'renew_months': 60,
     'description': 'Culture semi-hydroponique, substrat inerte.'},
]


EXPOSURES = [
    {'code': 'DEEP_SHADE', 'name': 'Ombre dense', 'min_lux': 0, 'max_lux': 500, 'rank': 1},
    {'code': 'SHADE', 'name': 'Ombre lumineuse', 'min_lux': 500, 'max_lux': 1500, 'rank': 2},
    {'code': 'MODERATE', 'name': 'Lumière modérée', 'min_lux': 1500, 'max_lux': 5000, 'rank': 3},
    {'code': 'BRIGHT_INDIRECT', 'name': 'Lumière vive indirecte', 'min_lux': 5000, 'max_lux': 10000, 'rank': 4},
    {'code': 'FILTERED_SUN', 'name': 'Soleil filtré', 'min_lux': 10000, 'max_lux': 20000, 'rank': 5},
    {'code': 'FULL_SUN', 'name': 'Plein soleil', 'min_lux': 20000, 'max_lux': 100000, 'rank': 6},
]


# min_HR / max_HR : humidité relative en %.
HUMIDITIES = [
    {'code': 'VERY_DRY', 'name': 'Très sec', 'min_HR': 0, 'max_HR': 30, 'rank': 1},
    {'code': 'DRY', 'name': 'Sec', 'min_HR': 30, 'max_HR': 40, 'rank': 2},
    {'code': 'MEDIUM', 'name': 'Moyen', 'min_HR': 40, 'max_HR': 55, 'rank': 3},
    {'code': 'HUMID', 'name': 'Humide', 'min_HR': 55, 'max_HR': 70, 'rank': 4},
    {'code': 'VERY_HUMID', 'name': 'Très humide', 'min_HR': 70, 'max_HR': 100, 'rank': 5},
]


# tolerancy_days_allowed : nombre de jours tolérés sans arrosage.
DROUGHT_TOLERANCES = [
    {'code': 'VERY_LOW', 'name': 'Très faible', 'tolerancy_days_allowed': 3, 'rank': 1},
    {'code': 'LOW', 'name': 'Faible', 'tolerancy_days_allowed': 7, 'rank': 2},
    {'code': 'MEDIUM', 'name': 'Moyenne', 'tolerancy_days_allowed': 14, 'rank': 3},
    {'code': 'HIGH', 'name': 'Bonne', 'tolerancy_days_allowed': 30, 'rank': 4},
    {'code': 'VERY_HIGH', 'name': 'Très bonne', 'tolerancy_days_allowed': 60, 'rank': 5},
]


REFERENTIALS = [
    (Action, ACTIONS),
    (Substrate, SUBSTRATES),
    (Exposure, EXPOSURES),
    (Humidity, HUMIDITIES),
    (DroughtTolerance, DROUGHT_TOLERANCES),
]


def run():
    counters = {}

    with transaction.atomic():
        for model, rows in REFERENTIALS:
            created = updated = 0

            for row in rows:
                defaults = {key: value for key, value in row.items() if key != 'code'}
                _, was_created = model.objects.update_or_create(code=row['code'], defaults=defaults)

                if was_created:
                    created += 1
                else:
                    updated += 1

            counters[model.__name__] = (created, updated)

    for name, (created, updated) in counters.items():
        print(f'{name:<18} {created:>3} créé(s), {updated:>3} mis à jour')
