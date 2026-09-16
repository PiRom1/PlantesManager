#!/usr/bin/env python3
"""
Télécharge depuis l'API GBIF un CSV d'espèces de plantes (orienté plantes
d'intérieur) avec un maximum de colonnes, à filtrer ensuite.

Stratégie : plutôt que de télécharger l'archive complète du GBIF Backbone
(~1,5 Go dont 99 % d'espèces hors sujet), on part d'une liste blanche de genres
cultivés en intérieur, on résout chaque genre en `genusKey`, puis on pagine les
espèces acceptées de ce genre. Chaque espèce est ensuite enrichie de ses noms
vernaculaires (toutes langues, FR et EN isolés dans leurs propres colonnes).

Usage :
    python scripts/download_gbif_indoor_plants.py
    python scripts/download_gbif_indoor_plants.py --out data/plantes.csv --workers 16
    python scripts/download_gbif_indoor_plants.py --core-only          # ~40 genres stars
    python scripts/download_gbif_indoor_plants.py --no-vernacular      # 10x plus rapide
    python scripts/download_gbif_indoor_plants.py --genera Monstera Ficus Hoya

Aucune dépendance externe : stdlib uniquement.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

API = "https://api.gbif.org/v1"
# Dataset key du GBIF Backbone Taxonomy : garantit une taxonomie unifiée
# (sinon on récupère les doublons de tous les datasets sources).
BACKBONE = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
USER_AGENT = "PlantesManager/1.0 (https://github.com/; contact: local script)"
# Garde-fou : aucun genre de plantes d'intérieur ne dépasse ~3000 espèces.
# Au-delà, c'est que la résolution du genre a dérapé vers un rang supérieur.
MAX_SPECIES_PER_GENUS = 5000

# --------------------------------------------------------------------------
# Liste blanche de genres.
#   core=True  -> genres classiques de plantes d'intérieur (le noyau utile)
#   core=False -> élargissement : plantes de véranda, agrumes, aromatiques,
#                 succulentes de collection, plantes de jardin courantes
# Ajoute/retire librement, c'est le seul endroit à toucher.
# --------------------------------------------------------------------------
GENERA: dict[str, bool] = {
    # --- Aracées : le coeur du hobby ---------------------------------------
    "Monstera": True, "Philodendron": True, "Epipremnum": True, "Scindapsus": True,
    "Anthurium": True, "Alocasia": True, "Colocasia": True, "Xanthosoma": True,
    "Aglaonema": True, "Dieffenbachia": True, "Spathiphyllum": True, "Syngonium": True,
    "Zamioculcas": True, "Caladium": True, "Amydrium": True, "Rhaphidophora": True,
    "Homalomena": True, "Cercestis": True, "Zantedeschia": True,
    # --- Marantacées (Calathea & co) ---------------------------------------
    "Goeppertia": True,  # ex-Calathea, genre accepté aujourd'hui
    "Calathea": True, "Maranta": True, "Ctenanthe": True, "Stromanthe": True,
    # --- Figuiers, moracées, urticacées ------------------------------------
    "Ficus": True, "Pilea": True, "Soleirolia": True,
    # --- Asparagacées / Dracaena / Sansevieria ------------------------------
    "Dracaena": True,  # absorbe Sansevieria dans la taxonomie moderne
    "Sansevieria": True, "Chlorophytum": True, "Asparagus": True, "Aspidistra": True,
    "Beaucarnea": True, "Cordyline": True, "Yucca": True, "Ophiopogon": True,
    "Liriope": True, "Agave": True, "Furcraea": True,
    # --- Broméliacées -------------------------------------------------------
    "Tillandsia": True, "Guzmania": True, "Vriesea": True, "Aechmea": True,
    "Neoregelia": True, "Billbergia": True, "Cryptanthus": True, "Ananas": True,
    # --- Palmiers & cycas ---------------------------------------------------
    "Chamaedorea": True, "Howea": True, "Dypsis": True, "Rhapis": True,
    "Livistona": True, "Phoenix": True, "Caryota": True, "Licuala": True,
    "Cycas": True, "Zamia": True,
    # --- Fougères -----------------------------------------------------------
    "Nephrolepis": True, "Adiantum": True, "Asplenium": True, "Platycerium": True,
    "Pteris": True, "Davallia": True, "Blechnum": True, "Polypodium": True,
    "Microsorum": True, "Phlebodium": True, "Cyrtomium": True, "Athyrium": False,
    # --- Succulentes & cactées ---------------------------------------------
    "Echeveria": True, "Crassula": True, "Sedum": True, "Haworthia": True,
    "Haworthiopsis": True, "Gasteria": True, "Aloe": True, "Kalanchoe": True,
    "Sempervivum": True, "Graptopetalum": True, "Pachyphytum": True, "Senecio": True,
    "Curio": True, "Portulacaria": True, "Lithops": True, "Conophytum": True,
    "Faucaria": True, "Adromischus": True, "Cotyledon": True, "Peperomia": True,
    "Schlumbergera": True, "Rhipsalis": True, "Epiphyllum": True, "Hatiora": True,
    "Mammillaria": True, "Gymnocalycium": True, "Echinopsis": True, "Parodia": True,
    "Astrophytum": True, "Ferocactus": True, "Opuntia": False, "Cereus": True,
    "Euphorbia": False,  # genre énorme (~2000 sp.), surtout non-intérieur
    "Stapelia": True, "Huernia": True, "Ceropegia": True, "Dischidia": True,
    # --- Apocynacées / lianes ----------------------------------------------
    "Hoya": True, "Adenium": True, "Plumeria": False, "Nerium": False,
    # --- Gesnériacées & fleuries d'intérieur --------------------------------
    "Saintpaulia": True, "Streptocarpus": True, "Episcia": True, "Aeschynanthus": True,
    "Columnea": True, "Sinningia": True, "Gloxinia": True,
    # --- Bégonias, oxalis, divers feuillages --------------------------------
    "Begonia": True, "Oxalis": True, "Fittonia": True, "Hypoestes": True,
    "Tradescantia": True, "Callisia": True, "Coleus": True, "Plectranthus": True,
    "Solenostemon": True, "Iresine": True, "Aphelandra": True, "Justicia": True,
    "Ruellia": True, "Strobilanthes": True, "Pellionia": True, "Pseudorhipsalis": True,
    # --- Grimpantes & suspensions ------------------------------------------
    "Cissus": True, "Hedera": True, "Parthenocissus": False, "Passiflora": False,
    "Stephanotis": True, "Jasminum": False, "Mandevilla": True, "Thunbergia": True,
    "Senna": False, "Clerodendrum": True,
    # --- Orchidées ----------------------------------------------------------
    "Phalaenopsis": True, "Dendrobium": True, "Cattleya": True, "Oncidium": True,
    "Cymbidium": True, "Paphiopedilum": True, "Vanda": True, "Miltonia": True,
    "Zygopetalum": True, "Bulbophyllum": False,
    # --- Carnivores ---------------------------------------------------------
    "Dionaea": True, "Drosera": True, "Nepenthes": True, "Sarracenia": True,
    "Pinguicula": True, "Utricularia": False,
    # --- Grandes plantes de véranda / intérieur lumineux --------------------
    "Strelitzia": True, "Musa": True, "Heliconia": True, "Alpinia": True,
    "Hedychium": False, "Costus": True, "Schefflera": True, "Heptapleurum": True,
    "Fatsia": True, "Fatshedera": True, "Polyscias": True, "Radermachera": True,
    "Araucaria": True, "Podocarpus": False, "Pachira": True, "Crassocephalum": False,
    "Codiaeum": True, "Acalypha": True, "Jatropha": True, "Pedilanthus": True,
    "Murraya": True, "Citrus": False, "Coffea": True, "Camellia": False,
    "Gardenia": True, "Ixora": True, "Hibiscus": False, "Bougainvillea": False,
    "Clivia": True, "Hippeastrum": True, "Amaryllis": True, "Eucharis": True,
    "Cyclamen": True, "Primula": False, "Saxifraga": False, "Aucuba": False,
    "Pittosporum": False, "Myrtus": False, "Laurus": False, "Olea": False,
    # --- Aromatiques & potager d'appui (élargissement) ----------------------
    "Ocimum": False, "Mentha": False, "Thymus": False, "Rosmarinus": False,
    "Salvia": False, "Origanum": False, "Petroselinum": False, "Lavandula": False,
    "Aloysia": False, "Melissa": False, "Capsicum": False, "Solanum": False,
    "Fragaria": False, "Lactuca": False,
}

FIELDNAMES = [
    # identité GBIF
    "gbif_key", "nub_key", "taxon_id", "dataset_key", "constituent_key",
    # noms
    "scientific_name", "canonical_name", "authorship", "name_type",
    "rank", "taxonomic_status", "nomenclatural_status",
    "accepted_key", "accepted_name", "parent_key", "parent",
    "basionym_key", "basionym", "published_in", "according_to", "origin",
    # classification complète
    "kingdom", "phylum", "class", "order", "family", "genus", "species",
    "kingdom_key", "phylum_key", "class_key", "order_key", "family_key",
    "genus_key", "species_key",
    # écologie / statut
    "num_descendants", "num_occurrences", "extinct", "habitats",
    "threat_statuses", "iucn_red_list_category",
    # vernaculaires
    "vernacular_fr", "vernacular_fr_all", "vernacular_en", "vernacular_en_all",
    "vernacular_count", "vernacular_languages", "vernacular_all_json",
    # métadonnées du script
    "genus_seed", "is_indoor_core", "gbif_url",
]

_print_lock = Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


def fetch(path: str, params: dict | None = None, retries: int = 5) -> dict:
    """GET sur l'API GBIF avec backoff exponentiel."""
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    delay = 1.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                log(f"  ! échec définitif {url} : {exc}")
                return {}
            time.sleep(delay)
            delay *= 2
    return {}


def resolve_genus(name: str) -> int | None:
    """Nom de genre -> genusKey du backbone.

    /species/match est capricieux : pour certains genres pourtant valides
    (Callisia, Fittonia, Goeppertia...) il renvoie matchType=HIGHERRANK avec la
    clé du PHYLUM. Accepter ce fallback fait paginer les 413 000 espèces de
    Tracheophyta. On exige donc un vrai rang GENUS, et on retombe sinon sur
    /species/search qui, lui, résout correctement ces cas.
    """
    data = fetch("/species/match", {"name": name, "rank": "GENUS", "kingdom": "Plantae", "strict": "false"})
    if data.get("rank") == "GENUS" and data.get("matchType") in ("EXACT", "FUZZY"):
        key = data.get("genusKey") or data.get("usageKey")
        if key:
            return key

    # Fallback : recherche plein texte restreinte au backbone, match exact sur
    # le nom canonique.
    data = fetch("/species/search", {
        "datasetKey": BACKBONE, "q": name, "rank": "GENUS", "status": "ACCEPTED", "limit": 20,
    })
    for r in data.get("results", []):
        if (r.get("canonicalName") or "").lower() == name.lower() and r.get("rank") == "GENUS":
            return r.get("key")
    return None


def list_species(genus_key: int, include_synonyms: bool, max_per_genus: int | None) -> list[dict]:
    """Toutes les espèces d'un genre, paginées."""
    out: list[dict] = []
    offset, limit = 0, 1000
    while True:
        params = {
            "datasetKey": BACKBONE,
            "highertaxonKey": genus_key,
            "rank": "SPECIES",
            "limit": limit,
            "offset": offset,
        }
        if not include_synonyms:
            params["status"] = "ACCEPTED"
        data = fetch("/species/search", params)
        if offset == 0 and data.get("count", 0) > MAX_SPECIES_PER_GENUS:
            log(f"  ! {data['count']} espèces annoncées (> {MAX_SPECIES_PER_GENUS}) : "
                f"genre suspect ou surdimensionné, tronqué")
        results = data.get("results", [])
        out.extend(results)
        if data.get("endOfRecords", True) or not results:
            break
        if len(out) >= (max_per_genus or MAX_SPECIES_PER_GENUS):
            break
        offset += limit
    return out[:max_per_genus or MAX_SPECIES_PER_GENUS]


def fetch_vernaculars(taxon_key: int) -> dict:
    """Noms vernaculaires d'un taxon, dédoublonnés et regroupés par langue."""
    data = fetch(f"/species/{taxon_key}/vernacularNames", {"limit": 500})
    results = data.get("results", [])
    by_lang: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for r in results:
        name = (r.get("vernacularName") or "").strip()
        lang = (r.get("language") or "und").strip()
        if not name or (lang, name.lower()) in seen:
            continue
        seen.add((lang, name.lower()))
        by_lang.setdefault(lang, []).append(name)
    fr = by_lang.get("fra", []) or by_lang.get("fre", [])
    en = by_lang.get("eng", [])
    return {
        "vernacular_fr": fr[0] if fr else "",
        "vernacular_fr_all": " | ".join(fr),
        "vernacular_en": en[0] if en else "",
        "vernacular_en_all": " | ".join(en),
        "vernacular_count": sum(len(v) for v in by_lang.values()),
        "vernacular_languages": ",".join(sorted(by_lang)),
        "vernacular_all_json": json.dumps(by_lang, ensure_ascii=False) if by_lang else "",
    }


def to_row(sp: dict, genus_seed: str, is_core: bool) -> dict:
    key = sp.get("key")
    return {
        "gbif_key": key,
        "nub_key": sp.get("nubKey"),
        "taxon_id": sp.get("taxonID"),
        "dataset_key": sp.get("datasetKey"),
        "constituent_key": sp.get("constituentKey"),
        "scientific_name": sp.get("scientificName"),
        "canonical_name": sp.get("canonicalName"),
        "authorship": sp.get("authorship"),
        "name_type": sp.get("nameType"),
        "rank": sp.get("rank"),
        "taxonomic_status": sp.get("taxonomicStatus"),
        "nomenclatural_status": ",".join(sp.get("nomenclaturalStatus") or []),
        "accepted_key": sp.get("acceptedKey"),
        "accepted_name": sp.get("accepted"),
        "parent_key": sp.get("parentKey"),
        "parent": sp.get("parent"),
        "basionym_key": sp.get("basionymKey"),
        "basionym": sp.get("basionym"),
        "published_in": sp.get("publishedIn"),
        "according_to": sp.get("accordingTo"),
        "origin": sp.get("origin"),
        "kingdom": sp.get("kingdom"),
        "phylum": sp.get("phylum"),
        "class": sp.get("class"),
        "order": sp.get("order"),
        "family": sp.get("family"),
        "genus": sp.get("genus"),
        "species": sp.get("species"),
        "kingdom_key": sp.get("kingdomKey"),
        "phylum_key": sp.get("phylumKey"),
        "class_key": sp.get("classKey"),
        "order_key": sp.get("orderKey"),
        "family_key": sp.get("familyKey"),
        "genus_key": sp.get("genusKey"),
        "species_key": sp.get("speciesKey"),
        "num_descendants": sp.get("numDescendants"),
        "num_occurrences": sp.get("numOccurrences"),
        "extinct": sp.get("extinct"),
        "habitats": ",".join(sp.get("habitats") or []),
        "threat_statuses": ",".join(sp.get("threatStatuses") or []),
        "iucn_red_list_category": sp.get("iucnRedListCategory"),
        "genus_seed": genus_seed,
        "is_indoor_core": is_core,
        "gbif_url": f"https://www.gbif.org/species/{key}" if key else "",
        # remplis plus tard (ou laissés vides avec --no-vernacular)
        "vernacular_fr": "", "vernacular_fr_all": "",
        "vernacular_en": "", "vernacular_en_all": "",
        "vernacular_count": "", "vernacular_languages": "", "vernacular_all_json": "",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="data/gbif_plantes.csv", help="chemin du CSV de sortie")
    p.add_argument("--workers", type=int, default=12, help="threads pour les noms vernaculaires")
    p.add_argument("--core-only", action="store_true", help="limiter aux genres d'intérieur classiques")
    p.add_argument("--no-vernacular", action="store_true", help="sauter les noms vernaculaires (bien plus rapide)")
    p.add_argument("--include-synonyms", action="store_true", help="inclure les synonymes, pas que les noms acceptés")
    p.add_argument("--max-per-genus", type=int, default=None, help="plafonner le nombre d'espèces par genre")
    p.add_argument("--genera", nargs="+", default=None, help="genres explicites, ignore la liste blanche")
    args = p.parse_args()

    if args.genera:
        genera = {g: True for g in args.genera}
    elif args.core_only:
        genera = {g: c for g, c in GENERA.items() if c}
    else:
        genera = dict(GENERA)

    log(f"→ {len(genera)} genres à traiter\n")

    rows: list[dict] = []
    seen_keys: set[int] = set()

    for i, (genus, is_core) in enumerate(sorted(genera.items()), 1):
        gkey = resolve_genus(genus)
        if not gkey:
            log(f"[{i}/{len(genera)}] {genus:<20} ✗ genre introuvable dans le backbone")
            continue
        species = list_species(gkey, args.include_synonyms, args.max_per_genus)
        added = 0
        for sp in species:
            key = sp.get("key")
            if key in seen_keys:  # un genre peut en absorber un autre (Sansevieria -> Dracaena)
                continue
            seen_keys.add(key)
            rows.append(to_row(sp, genus, is_core))
            added += 1
        log(f"[{i}/{len(genera)}] {genus:<20} key={gkey:<10} {added:>5} espèces (total {len(rows)})")

    log(f"\n→ {len(rows)} espèces uniques collectées")

    if not args.no_vernacular:
        log(f"→ récupération des noms vernaculaires ({args.workers} threads)…")
        done = [0]

        def enrich(row: dict) -> None:
            row.update(fetch_vernaculars(row["gbif_key"]))
            done[0] += 1
            if done[0] % 500 == 0:
                log(f"   {done[0]}/{len(rows)}")

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(enrich, rows))

    out_path = args.out
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    size_mb = os.path.getsize(out_path) / 1_048_576
    with_fr = sum(1 for r in rows if r.get("vernacular_fr"))
    log(f"\n✓ {out_path} — {len(rows)} lignes, {len(FIELDNAMES)} colonnes, {size_mb:.1f} Mo")
    log(f"  dont {with_fr} espèces avec un nom vernaculaire français")
    return 0


if __name__ == "__main__":
    sys.exit(main())
