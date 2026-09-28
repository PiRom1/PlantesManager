from io import BytesIO
from math import sqrt
from urllib.parse import urlparse
from pathlib import PurePosixPath

import requests
from PIL import Image
from django.core.files.base import ContentFile

from Plantes.models import Specie



def fetch_available_gbif_images(gbif_id: int) -> list[dict]:
    """
    Photos d'observations (pas d'herbier) pour un taxon GBIF.
    Chaque élément : {"id", "url", "site", "author", "license"}.
    """

    data = requests.get(
        "https://api.gbif.org/v1/occurrence/search",
        params={"taxonKey": gbif_id, "mediaType": "StillImage", "basisOfRecord": "HUMAN_OBSERVATION", "limit": 20},
    ).json()

    images = []
    for occurrence in data.get("results", []):
        for i, m in enumerate(occurrence.get("media", [])):
            if m.get("type") != "StillImage" or not m.get("identifier"):
                continue
            url = m["identifier"]
            images.append({
                # page de la photo chez l'éditeur (ex. inaturalist.org/photos/123), sinon clé d'occurrence GBIF + index
                "id": m.get("references") or f"gbif:{occurrence['key']}#{i}",
                "url": url,
                # éditeur déclaré (ex. "iNaturalist"), sinon domaine hébergeant le fichier
                "site": m.get("publisher") or urlparse(url).hostname,
                "author": m.get("creator") or m.get("rightsHolder") or occurrence.get("recordedBy"),
                "license": m.get("license"),
            })

    return images


TARGET_PIXELS = 1_000_000  # surface cible (largeur × hauteur) après redimensionnement
JPEG_QUALITY = 85


def download_image(url: str) -> ContentFile:
    """Télécharge l'image, la ramène à ~TARGET_PIXELS en conservant le ratio, et la renvoie en JPEG."""

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    image = Image.open(BytesIO(response.content))
    image = image.convert("RGB")  # PNG avec alpha, palette, CMYK... → RGB pour le JPEG

    width, height = image.size
    scale = sqrt(TARGET_PIXELS / (width * height))
    if scale < 1:  # on réduit seulement, jamais d'agrandissement
        image = image.resize((round(width * scale), round(height * scale)), Image.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)

    filename = PurePosixPath(urlparse(url).path).stem or "image"
    return ContentFile(buffer.getvalue(), name=f"{filename}.jpg")




def run():

    species_without_image = Specie.objects.filter(image = '').order_by('?')
    print(f"{len(species_without_image)} espèces sans image.")

    for i,specie in enumerate(species_without_image):

        

        try:
            specie_data = fetch_available_gbif_images(gbif_id=specie.gbif_key)
            specie.image.save(name = f"{specie.gbif_key}.jpg", content = download_image(specie_data[0].get('url')))
            print(f"[{i}/{species_without_image.count()}] Photo enregistrée pour l'espèce {specie.gbif_key} !")
            

        except Exception as e:
            print(f"[{i}/{species_without_image.count()}] Erreur pour récupérer les images de l'espèce {specie.gbif_key} : {e}")

        