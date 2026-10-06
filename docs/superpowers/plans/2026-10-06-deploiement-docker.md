# Déploiement Docker — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire tourner PlantesManager dans un container Docker sur le serveur maison, derrière un reverse proxy existant, base reconstruite au démarrage, médias montés en volume.

**Architecture:** Un seul service `web` (uvicorn ASGI). Whitenoise sert les statiques, une vue Django `login_required` sert les médias. Un entrypoint idempotent migre, peuple, raccroche les images d'espèces déjà sur disque et crée le superuser. SQLite et `media/` vivent dans `deploy/` sur l'hôte.

**Tech Stack:** Django 6.1, uvicorn, whitenoise, Pillow, Docker Compose, python:3.12-slim.

**Spec:** `docs/superpowers/specs/2026-10-06-deploiement-docker-design.md`

## Global Constraints

- Pas de tests unitaires (décision de Romain, 06/10/2026). La seule vérification est le bout en bout du container en Task 5.
- Ne jamais lancer `manage.py migrate` ni les `runscript` sur la base de dev `PlantesManager/db.sqlite3`. Le container écrit dans `deploy/db/`, c'est le seul endroit où ça tourne.
- Chaque réglage de `settings.py` garde sa valeur actuelle quand la variable d'environnement est absente : le dev de Romain ne change pas.
- Style : vues fonction simples, commentaires en français, deux lignes vides entre fonctions. Copier la forme des vues existantes.
- Pas de nouvelle migration : aucun modèle ne change.
- Commits préfixés `[ADD]` / `[UPD]`, terminés par `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Commandes locales avec `.venv/bin/python`.

## Review Focus

Vérifiés à la main en Task 5, faute de tests :
1. `ALLOWED_HOSTS` avec espaces autour des virgules → `env_list` fait `strip()`.
2. Dossier `media/SpecieImages/unsorted/` ou nom non numérique → ignoré par `link_specie_images`.
3. Dossier d'espèce vide → ignoré, pas de chemin fantôme en base.
4. `/media/../PlantesManager/settings.py` → 404 (garanti par `django.views.static.serve`).
5. Second démarrage du container → rien en double, pas d'échec sur `createsuperuser`.

---

### Task 1 : Dépendances et settings déployables

**Files:**
- Modify: `requirements.txt`
- Modify: `PlantesManager/settings.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: variables `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_PATH`, `MEDIA_ROOT` lues dans `settings.py` ; `STATIC_ROOT = <racine>/staticfiles`.

- [ ] **Step 1 : Modifier `settings.py`**

Juste après `load_dotenv(BASE_DIR / '.env')` :

```python
def env_list(name, default):
    """
    Liste lue dans l'environnement, séparateur virgule, espaces tolérés.
    Variable absente → `default`. Variable vide → liste vide.
    """

    value = os.environ.get(name)
    if value is None:
        return default

    return [item.strip() for item in value.split(',') if item.strip()]
```

Remplacer le bloc `MEDIA_URL` / `MEDIA_ROOT` :

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media/'))
```

Remplacer `ALLOWED_HOSTS = [...]` et `CSRF_TRUSTED_ORIGINS = [...]` :

```python
# En prod : ALLOWED_HOSTS=plantes.exemple.fr et CSRF_TRUSTED_ORIGINS=https://plantes.exemple.fr
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['127.0.0.1', 'localhost'])

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', [])
```

Dans `MIDDLEWARE`, insérer `'whitenoise.middleware.WhiteNoiseMiddleware',` juste après `'django.middleware.security.SecurityMiddleware',`.

Remplacer `DATABASES` :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DATABASE_PATH', BASE_DIR / 'PlantesManager/db.sqlite3'),
    }
}
```

Remplacer `STATIC_ROOT = os.path.join(BASE_DIR, 'Plantes/static')` :

```python
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

Remplacer les deux dernières lignes (`SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE`) :

```python
SESSION_COOKIE_SAMESITE = 'Lax'

# Derrière le reverse proxy HTTPS du serveur : cookies Secure et détection du schéma
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

- [ ] **Step 2 : Dépendances**

`requirements.txt` :

```
django
django-extensions
djangorestframework
channels
uvicorn[standard]
python-dotenv
requests
pillow
whitenoise
```

- [ ] **Step 3 : Gitignore**

Ajouter à `.gitignore` :

```
staticfiles/
deploy/db/
deploy/media/
```

- [ ] **Step 4 : Vérifier que le dev ne change pas**

Run : `.venv/bin/python manage.py check`
Attendu : `System check identified no issues`.

Run : `.venv/bin/python -c "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='PlantesManager.settings'; django.setup(); from django.conf import settings as s; print(s.ALLOWED_HOSTS, s.DEBUG, s.DATABASES['default']['NAME'], s.STATIC_ROOT)"`
Attendu : `['127.0.0.1', 'localhost'] True .../PlantesManager/db.sqlite3 .../staticfiles`.

Run : `DEBUG=False ALLOWED_HOSTS=' a, b ' .venv/bin/python -c "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='PlantesManager.settings'; django.setup(); from django.conf import settings as s; print(s.ALLOWED_HOSTS, s.SESSION_COOKIE_SECURE)"`
Attendu : `['a', 'b'] True`.

- [ ] **Step 5 : Commit**

```bash
git add requirements.txt PlantesManager/settings.py .gitignore
git commit -m "[UPD] Settings pilotés par l'environnement pour le déploiement

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2 : Route média réservée aux utilisateurs connectés

**Files:**
- Create: `Plantes/views/media_views.py`
- Modify: `Plantes/urls.py`
- Modify: `PlantesManager/urls.py`

**Interfaces:**
- Consumes: `MEDIA_ROOT` (Task 1).
- Produces: vue `serve_media(request, path)`, route `media/<path:path>` nommée `serve_media`.

- [ ] **Step 1 : Écrire la vue**

`Plantes/views/media_views.py` :

```python
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.static import serve


@login_required
def serve_media(request, path):

    # Photos de plantes et d'espèces : réservées aux utilisateurs connectés.
    # django.views.static.serve refuse les chemins qui remontent hors de MEDIA_ROOT.
    return serve(request, path, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 2 : Brancher la route**

`Plantes/urls.py`, import :

```python
from Plantes.views import media_views, plant_views, pot_views, species_views, spot_views
```

En fin de `urlpatterns` :

```python
    # Médias (photos), servis uniquement aux utilisateurs connectés
    path('media/<path:path>', media_views.serve_media, name='serve_media'),
```

`PlantesManager/urls.py`, sans les `static()` :

```python
"""
URL configuration for PlantesManager project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('Plantes.urls')),
    path('admin/', admin.site.urls),
]
```

- [ ] **Step 3 : Vérifier en dev**

Run : `.venv/bin/python manage.py runserver` (autre terminal) puis :

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/static/Plantes/css/base.css
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/media/SpecieImages/10030768/10030768.jpg
```

Attendu : `200` (whitenoise avec finders en DEBUG, pas de collectstatic nécessaire), `302` vers le login. Arrêter runserver.

- [ ] **Step 4 : Commit**

```bash
git add Plantes/views/media_views.py Plantes/urls.py PlantesManager/urls.py
git commit -m "[UPD] Médias servis par Django et réservés aux utilisateurs connectés

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3 : Script `link_specie_images`

**Files:**
- Create: `Plantes/scripts/link_specie_images.py`

**Interfaces:**
- Consumes: modèle `Specie` (`gbif_key` BigInteger unique nullable, `image` ImageField nullable, chemins `SpecieImages/<gbif_key>/<fichier>`).
- Produces: `link_specie_images(media_root) -> int` et `run()` pour `manage.py runscript link_specie_images`.

- [ ] **Step 1 : Écrire le script**

```python
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
```

- [ ] **Step 2 : Vérifier l'import**

Run : `.venv/bin/python -c "import os, django; os.environ['DJANGO_SETTINGS_MODULE']='PlantesManager.settings'; django.setup(); import Plantes.scripts.link_specie_images"`
Attendu : aucune sortie. Ne pas lancer `run()` sur la base de dev.

- [ ] **Step 3 : Commit**

```bash
git add Plantes/scripts/link_specie_images.py
git commit -m "[ADD] Script link_specie_images pour raccrocher les images déjà sur disque

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4 : Dockerfile, entrypoint, compose, `.env_example`

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `deploy/entrypoint.sh`
- Create: `docker-compose.yml`
- Modify: `.env_example`

**Interfaces:**
- Consumes: Task 1 et Task 3.
- Produces: image buildable, container écoutant sur 8000.

- [ ] **Step 1 : `.dockerignore`**

Sans lui, 880 Mo de `media/` et le venv partent dans le contexte de build.

```
.git
.venv
venv
__pycache__
*.pyc
*.sqlite3
.env
media
deploy/db
deploy/media
staticfiles
.pytest_cache
.superpowers
docs
```

- [ ] **Step 2 : `Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Statiques collectés dans l'image, servis par whitenoise
RUN python manage.py collectstatic --noinput

RUN chmod +x deploy/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["deploy/entrypoint.sh"]
CMD ["uvicorn", "PlantesManager.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3 : `deploy/entrypoint.sh`**

```bash
#!/bin/sh
# Démarrage du container : base à jour, référentiels peuplés, images raccrochées,
# superuser créé si demandé. Toutes les étapes sont idempotentes.
set -e

python manage.py migrate --noinput
python manage.py runscript populate_abiotic_database
python manage.py runscript populate_plant_states
python manage.py runscript populate_species_database
python manage.py runscript link_specie_images

# Superuser au premier démarrage, seulement si le .env le demande et qu'il n'y en a aucun
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    if python manage.py shell -c "import sys; from Plantes.models import User; sys.exit(0 if User.objects.filter(is_superuser=True).exists() else 1)"; then
        echo "Un superuser existe déjà, création ignorée."
    else
        python manage.py createsuperuser --noinput
    fi
fi

exec "$@"
```

`chmod +x deploy/entrypoint.sh`. Après `git add`, `git ls-files -s deploy/entrypoint.sh` doit montrer `100755`.

- [ ] **Step 4 : `docker-compose.yml`**

```yaml
services:
  web:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_PATH: /data/db/db.sqlite3
      MEDIA_ROOT: /app/media
    ports:
      - "${PORT:-8000}:8000"
    volumes:
      - ./deploy/db:/data/db
      - ./deploy/media:/app/media
```

- [ ] **Step 5 : `.env_example`**

Remplacer la section Django par :

```
# Django
SECRET_KEY=change-me
DEBUG=True

# Déploiement (voir README, section Déploiement). Sans ces variables, les valeurs
# de développement s'appliquent : hôtes 127.0.0.1 et localhost, port 8000.
# ALLOWED_HOSTS=plantes.exemple.fr
# CSRF_TRUSTED_ORIGINS=https://plantes.exemple.fr
# PORT=8000

# Superuser créé automatiquement au premier démarrage du container, si aucun n'existe.
# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_EMAIL=admin@exemple.fr
# DJANGO_SUPERUSER_PASSWORD=change-me
```

Le reste (Telegram) ne change pas.

- [ ] **Step 6 : Construire**

Run : `docker compose build`
Attendu : build OK, `collectstatic` affiche `N static files copied to '/app/staticfiles'`.

- [ ] **Step 7 : Commit**

```bash
git add Dockerfile .dockerignore deploy/entrypoint.sh docker-compose.yml .env_example
git commit -m "[ADD] Dockerfile, entrypoint et docker compose

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5 : Bout en bout dans le container

**Files:** aucun fichier du dépôt. `.env` de test dans le scratchpad, données dans `deploy/` local (gitignoré).

- [ ] **Step 1 : `.env` de test, séparé du `.env` de dev**

Fichier `<scratchpad>/env.test` :

```
SECRET_KEY=test-only-not-secret
DEBUG=False
ALLOWED_HOSTS=localhost, 127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8001
PORT=8001
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@exemple.fr
DJANGO_SUPERUSER_PASSWORD=motdepasse-test
```

L'espace après la virgule dans `ALLOWED_HOSTS` est voulu (Review Focus 1).

Médias factices couvrant les Review Focus 2 et 3 :

```bash
mkdir -p deploy/db deploy/media/SpecieImages/unsorted deploy/media/SpecieImages/10106327
cp -r media/SpecieImages/10030768 media/SpecieImages/10065044 deploy/media/SpecieImages/
cp media/SpecieImages/10030768/*.jpg deploy/media/SpecieImages/unsorted/perdu.jpg
# 10106327 reste vide
```

- [ ] **Step 2 : Démarrer**

Run : `docker compose --env-file <scratchpad>/env.test up -d --build && docker compose logs -f web`
Attendu dans l'ordre : migrations appliquées, référentiels, `N espèce(s) créée(s)` (environ 3 100), `2 image(s) d'espèce raccrochée(s).`, `Superuser created successfully.`, `Uvicorn running on http://0.0.0.0:8000`.

- [ ] **Step 3 : HTTP**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8001/accounts/login/
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8001/static/Plantes/css/base.css
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8001/media/SpecieImages/10030768/10030768.jpg
curl -s -o /dev/null -w '%{http_code}\n' --path-as-is http://localhost:8001/media/../PlantesManager/settings.py
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: pirate.exemple.fr' http://localhost:8001/accounts/login/
```

Attendu : `200`, `200`, `302`, `404` ou `302` (la vue redirige avant de servir, les deux sont bons), `400`.

Connecté, page d'espèce et image :

```bash
docker compose exec web python manage.py shell -c "
from django.test import Client
from Plantes.models import User, Specie
c = Client(HTTP_HOST='localhost')
c.force_login(User.objects.get(username='admin'))
s = Specie.objects.get(gbif_key=10030768)
print(c.get(f'/specie/{s.pk}/').status_code, c.get(s.image.url).status_code)
print(Specie.objects.get(gbif_key=10106327).image.name or 'vide')
print(c.get('/media/../PlantesManager/settings.py').status_code)
"
```

Attendu : `200 200`, `vide`, `404`.

- [ ] **Step 4 : Redémarrage idempotent (Review Focus 5)**

Run : `docker compose --env-file <scratchpad>/env.test restart web && docker compose logs --since 1m web`
Attendu : `Aucune nouvelle espèce à importer.`, `0 image(s) d'espèce raccrochée(s).`, `Un superuser existe déjà, création ignorée.`, uvicorn redémarre. Aucune erreur.

- [ ] **Step 5 : La base de dev n'a pas bougé**

Run : `ls -la PlantesManager/db.sqlite3`
Attendu : date inchangée (1er octobre 16:58 au début de la session).

- [ ] **Step 6 : Nettoyer**

```bash
docker compose --env-file <scratchpad>/env.test down
rm -rf deploy/db deploy/media
```

---

### Task 6 : README, section Déploiement

**Files:**
- Modify: `README.md` (nouvelle section entre « 🖥️ Lancer » et « 🔧 Configuration », et lignes dans le tableau Configuration)

- [ ] **Step 1 : Section**

````markdown
## 🐳 Déploiement

L'application tourne dans un container, derrière ton reverse proxy (HTTPS et nom
de domaine restent de son ressort). SQLite et les photos vivent dans `deploy/` à
côté du code : sauvegarder, c'est copier ce dossier.

```bash
git clone <ce dépôt> && cd PlantesManager
cp .env_example .env          # puis remplir SECRET_KEY, DEBUG=False, ALLOWED_HOSTS,
                              # CSRF_TRUSTED_ORIGINS, PORT, DJANGO_SUPERUSER_*
docker compose up -d --build
```

Au démarrage, le container applique les migrations, peuple les référentiels et le
catalogue d'espèces, raccroche les images déjà présentes dans `deploy/media/` et
crée le superuser si aucun n'existe. Tout est idempotent : chaque redémarrage
rejoue ces étapes sans rien dupliquer.

### 🖼️ Récupérer tes images d'espèces

Les photos ne sont pas dans git. Depuis la machine qui les a :

```bash
rsync -a media/ serveur:/chemin/PlantesManager/deploy/media/
```

Puis `docker compose restart web` : les images sont raccrochées aux espèces.
Sans ces fichiers, `docker compose exec web python manage.py runscript fetch_specie_images`
en télécharge depuis GBIF (long).

### 🔄 Mettre à jour

```bash
git pull && docker compose up -d --build
```

### 🧯 Si ça ne répond pas

| Symptôme | Cause probable |
|---|---|
| `400 Bad Request` | `ALLOWED_HOSTS` ne contient pas le nom de domaine |
| `403 CSRF` à la connexion | `CSRF_TRUSTED_ORIGINS` sans le `https://` ou mauvais domaine |
| Photos en 404 | `deploy/media/` vide ou droits de lecture |

`docker compose logs web` montre le détail.
````

Tableau « 🔧 Configuration », lignes à ajouter :

```markdown
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | `127.0.0.1,localhost` / vide |
| `DATABASE_PATH`, `MEDIA_ROOT` | `PlantesManager/db.sqlite3` / `media/` |
| `DJANGO_SUPERUSER_USERNAME`, `_EMAIL`, `_PASSWORD` | non définis : pas de création automatique |
```

- [ ] **Step 2 : Commit**

```bash
git add README.md
git commit -m "[UPD] README : section Déploiement Docker

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```
