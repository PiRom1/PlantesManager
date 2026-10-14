"""
Ressemblance entre noms d'espèces, pour prévenir les doublons quand une espèce
est créée à la main.

Bibliothèque standard (difflib) plutôt qu'une dépendance Levenshtein : le ratio
est du même esprit, et les noms sont d'abord normalisés (minuscules, sans
accents ni espaces superflus) pour que « Ficus Élastica » et « ficus elastica »
se valent.
"""

import unicodedata
from difflib import SequenceMatcher

from Plantes.models import Specie


SIMILARITY_THRESHOLD = 0.85
SIMILAR_LIMIT = 3


def normalize(name):
    """Minuscules, sans accents, espaces réduits : la forme comparée."""

    text = unicodedata.normalize('NFKD', name or '')
    text = ''.join(char for char in text if not unicodedata.combining(char))

    return ' '.join(text.lower().split())


def similarity(a, b):
    """Ratio difflib entre deux noms normalisés, de 0 à 1."""

    matcher = SequenceMatcher(None, a, b)

    # Bornes rapides avant le calcul complet : ~3 000 espèces à parcourir
    if matcher.real_quick_ratio() < SIMILARITY_THRESHOLD or matcher.quick_ratio() < SIMILARITY_THRESHOLD:
        return 0.0

    return matcher.ratio()


def similar_species(vernacular_name, scientific_name, exclude_id=None):
    """
    Espèces du catalogue dont le nom vernaculaire ou scientifique ressemble à
    l'un des deux noms proposés : [(espèce, pourcentage)], les plus proches
    d'abord, au plus SIMILAR_LIMIT, au-dessus de SIMILARITY_THRESHOLD.
    """

    wanted = [normalize(name) for name in (vernacular_name, scientific_name) if name and name.strip()]

    if not wanted:
        return []

    species = Specie.objects.only('id', 'vernacular_name', 'scientific_name')
    if exclude_id:
        species = species.exclude(id=exclude_id)

    matches = []

    for specie in species:
        candidates = [normalize(specie.vernacular_name), normalize(specie.scientific_name)]
        score = max(similarity(a, b) for a in wanted for b in candidates)

        if score >= SIMILARITY_THRESHOLD:
            matches.append((specie, round(score * 100)))

    matches.sort(key=lambda match: -match[1])

    return matches[:SIMILAR_LIMIT]
