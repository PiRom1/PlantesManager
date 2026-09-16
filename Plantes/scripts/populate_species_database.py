"""
Peuple la table Specie à partir du CSV GBIF.

Usage :
    python manage.py runscript populate_species_database

Sont importées les espèces d'un genre d'intérieur (is_indoor_core) ET possédant
un nom vernaculaire français ou anglais. Le nom français prime ; à défaut on
retombe sur l'anglais. Les noms sont conservés tels quels, séparés par des
virgules quand il y en a plusieurs.

Idempotent : les espèces déjà en base (clé = gbif_key) sont ignorées.
Le CSV ne contient aucune donnée abiotique : exposition, humidité, tolérance
à la sécheresse, températures et substrat restent donc à NULL.
"""

import csv

from django.conf import settings
from django.db import transaction

from Plantes.models import Specie


CSV_PATH = settings.BASE_DIR / 'data' / 'gbif_plantes.csv'

BATCH_SIZE = 500


def read_species(existing_keys):
    """Lit le CSV et retourne les Specie à créer (non sauvegardées)."""
    species = []

    with open(CSV_PATH, encoding='utf-8') as csv_file:
        for row in csv.DictReader(csv_file):

            # Genre de plante d'intérieur, et nommée en français ou en anglais
            vernacular_fr = row['vernacular_fr'].strip()
            vernacular_en = row['vernacular_en'].strip()

            if row['is_indoor_core'] != 'True':
                continue
            if not vernacular_fr and not vernacular_en:
                continue

            gbif_key = int(row['gbif_key'])
            if gbif_key in existing_keys:
                continue

            species.append(Specie(
                gbif_key=gbif_key,
                vernacular_name=vernacular_fr or vernacular_en,
                vernacular_name_en=vernacular_en or None,
                scientific_name=row['canonical_name'].strip() or row['scientific_name'].strip(),
                taxon_class=row['class'].strip() or None,
                taxon_order=row['order'].strip() or None,
                taxon_family=row['family'].strip() or None,
                taxon_genus=row['genus'].strip() or None,
            ))

    return species


def run():
    existing_keys = set(Specie.objects.values_list('gbif_key', flat=True))
    species = read_species(existing_keys)

    if not species:
        print('Aucune nouvelle espèce à importer.')
        return

    with transaction.atomic():
        Specie.objects.bulk_create(species, batch_size=BATCH_SIZE)

    print(f'{len(species)} espèce(s) créée(s), {len(existing_keys)} déjà en base.')
