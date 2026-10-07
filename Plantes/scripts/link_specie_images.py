"""
Raccroche aux espèces les images déjà présentes sur disque.

Usage :
    python manage.py runscript link_specie_images

Les images d'espèces sont rangées en media/SpecieImages/<gbif_key>/<fichier>.
Quand la base est reconstruite (déploiement) mais que media/ a été copié, ce
script renseigne Specie.image pour chaque espèce qui n'en a pas et dont le
dossier contient au moins un fichier. Rien n'est copié ni ouvert.

Idempotent : une espèce qui a déjà une image n'est pas touchée.
"""

from pathlib import Path

from django.conf import settings
from django.db.models import Q

from Plantes.models import Specie


def link_specie_images(media_root):
    """Renseigne Specie.image depuis <media_root>/SpecieImages/, retourne le nombre d'espèces raccrochées."""

    species_dir = Path(media_root) / 'SpecieImages'
    if not species_dir.is_dir():
        return 0

    # Espèces sans image, indexées par clé GBIF
    without_image = Specie.objects.filter(Q(image='') | Q(image__isnull=True), gbif_key__isnull=False)
    by_gbif_key = {specie.gbif_key: specie for specie in without_image}

    linked = []
    for folder in species_dir.iterdir():

        if not folder.is_dir() or not folder.name.isdigit():
            continue

        specie = by_gbif_key.get(int(folder.name))
        if specie is None:
            continue

        files = sorted(f for f in folder.iterdir() if f.is_file())
        if not files:
            continue

        specie.image.name = f'SpecieImages/{folder.name}/{files[0].name}'
        linked.append(specie)

    Specie.objects.bulk_update(linked, ['image'], batch_size=500)

    return len(linked)


def run():

    count = link_specie_images(settings.MEDIA_ROOT)
    print(f'{count} image(s) d\'espèce raccrochée(s).')
