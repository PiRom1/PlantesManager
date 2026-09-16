# 🪴 PlantesManager

> Ton jardin d'intérieur, en base de données.

Catalogue d'espèces, suivi de ta collection, journal d'entretien et règles de soin.
Parce qu'il faut bien se souvenir de la dernière fois qu'on a arrosé le Monstera. 💧

---

## 🌱 Le principe

L'application sépare **le catalogue** 📚 (partagé, issu de GBIF) de **ta collection** 🏡
(tes plantes, tes emplacements, tes pots).

| | Modèle | Rôle |
|---|---|---|
| 🌿 | `Specie` | Une espèce du catalogue : noms FR/EN, taxonomie, exigences abiotiques |
| 🪴 | `Plant` | **Ta** plante : une espèce, un cultivar, un emplacement, un pot, un substrat |
| 🪟 | `Spot` | Un endroit de ta maison aux conditions homogènes (lumière, humidité, températures) |
| 🏺 | `Pot` | Un contenant, avec son facteur de séchage |
| 📖 | `PlantHistory` | Le journal : chaque action réalisée, avec photo, mesures et détails |
| ⏰ | `CareRule` | La cadence d'une action, par espèce (défaut) ou par plante (surcharge) |

Les référentiels (`Action`, `Substrate`, `Exposure`, `Humidity`, `DroughtTolerance`,
`PlantState`) sont des échelles fixes, peuplées par des scripts.

### ✨ Le détail des actions

Chaque action porte son propre jeu de champs de saisie, déclaré dans
`Action.DETAIL_FIELDS` (`Plantes/models.py`). Un arrosage 💧 demande le type d'eau,
le volume et la méthode ; un bouturage 🌱 demande la méthode, le milieu et le nombre
de boutures. Les valeurs saisies sont compilées en JSON dans `PlantHistory.detail`.

> 🎯 **C'est la seule source de vérité.** Ajouter un champ à une action le fait
> apparaître dans le formulaire, valider au POST et afficher dans l'historique —
> sans toucher ni à la vue, ni au template, ni au JavaScript.

---

## 📦 Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 Initialisation

```bash
# 1️⃣  Base de données
python manage.py migrate

# 2️⃣  Compte administrateur
python manage.py createsuperuser

# 3️⃣  Référentiels (échelles, actions, substrats, états)
python manage.py runscript populate_abiotic_database
python manage.py runscript populate_plant_states

# 4️⃣  Catalogue d'espèces (nécessite data/gbif_plantes.csv)
python manage.py runscript populate_species_database
```

♻️ Les scripts de peuplement sont **idempotents** : relance-les autant que tu veux,
ils mettent à jour l'existant sans créer de doublon.

### 🗂️ Le fichier d'espèces

`populate_species_database` lit `data/gbif_plantes.csv`. S'il est absent,
régénère-le depuis l'API GBIF :

```bash
python scripts/download_gbif_indoor_plants.py
```

L'import ne retient que les espèces d'un genre d'intérieur **et** disposant d'un
nom vernaculaire français ou anglais — soit environ **3 100 espèces** sur les 47 000
du fichier.

> ⚠️ Le CSV ne contient **aucune donnée abiotique** : exposition, humidité,
> tolérance à la sécheresse et températures restent à remplir à la main.

---

## 🖥️ Lancer

```bash
python manage.py runserver
```

| | URL | Page |
|---|---|---|
| 🌿 | `/species/` | Catalogue des espèces (paginé) |
| 🪴 | `/plants/` | Mes plantes |
| 🪟 | `/spots/` | Mes emplacements |
| 🏺 | `/pots/` | Mes pots |
| ⚙️ | `/admin/` | Administration Django |

🔒 Toutes les pages demandent une connexion (`/accounts/login/`).

---

## 🔧 Configuration

Les réglages sensibles se lisent dans l'environnement, avec des valeurs de repli
adaptées au développement :

| Variable | Défaut |
|---|---|
| `SECRET_KEY` | valeur de développement — 🚨 **à définir en production** |
| `DEBUG` | `True` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | vide |

💾 La base est un SQLite dans `PlantesManager/db.sqlite3`.

---

<p align="center">Bon jardinage 🌿</p>
