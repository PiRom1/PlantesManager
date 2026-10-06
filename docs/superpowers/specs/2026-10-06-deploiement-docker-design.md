# Déploiement Docker de PlantesManager — design

Date : 2026-10-06

## Objectif

Déployer PlantesManager sur le serveur maison de Romain dans un container, derrière
son reverse proxy existant (HTTPS et nom de domaine gérés hors du projet). Le
déploiement doit aussi fonctionner pour quelqu'un qui clone le dépôt sans aucune
donnée : la base est reconstruite par les migrations et les scripts de peuplement.

Ce qui est transféré depuis la machine de dev : uniquement `media/` (880 Mo,
3 333 images d'espèces + quelques photos de plantes). La base SQLite n'est pas
transférée.

## Hors périmètre

- Le service cron Telegram (résumé quotidien). Il viendra plus tard comme second
  service du compose, même image. Rien n'est prévu pour lui aujourd'hui, sauf que le
  `.env` conserve ses variables.
- Reverse proxy et TLS : fournis par le serveur.
- Sauvegardes : un `cp` du dossier `deploy/` suffit, c'est l'intérêt de SQLite en
  volume. Pas d'outillage.
- CI, registry d'images : le serveur clone et construit localement.
- Postgres : refusé. Déclencheur pour y revenir : écritures concurrentes de
  plusieurs utilisateurs.
- Sidecar nginx : refusé. Déclencheur : plusieurs utilisateurs ou lenteur sur les
  pages d'images.

## Architecture

Un seul service `web`. Uvicorn sert l'application ASGI (channels est installé, le
routage websocket est vide, un seul worker suffit). Whitenoise sert les fichiers
statiques. Les médias sont servis par Django via une route explicite, réservée aux
utilisateurs connectés.

```
reverse proxy (hôte)  →  web:8000 (uvicorn)
                              ├─ /static/   whitenoise
                              ├─ /media/    vue Django, login_required
                              └─ /…         Django
volumes hôte :  ./deploy/db     →  /data/db     (db.sqlite3)
                ./deploy/media  →  /app/media
```

## Composants

### 1. `Dockerfile`

- Base `python:3.12-slim`.
- Installe `requirements.txt`, copie le code, lance `collectstatic --noinput` au build.
- `requirements.txt` gagne `pillow` et `whitenoise` : ils sont dans le venv de dev
  mais pas déclarés, une image neuve casserait sans eux.
- Entrypoint : `deploy/entrypoint.sh` (voir 4). Commande : uvicorn sur
  `PlantesManager.asgi:application`, hôte `0.0.0.0`, port 8000.

### 2. `settings.py` déployable sans changer le dev

Chaque réglage garde sa valeur actuelle quand la variable d'environnement est absente.

| Variable | Défaut (dev) | Rôle |
|---|---|---|
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | liste séparée par des virgules |
| `CSRF_TRUSTED_ORIGINS` | vide | liste séparée par des virgules, ex. `https://plantes.exemple.fr` |
| `DATABASE_PATH` | `PlantesManager/db.sqlite3` | chemin du fichier SQLite |
| `MEDIA_ROOT` | `<racine>/media/` | dossier des médias |

Changements fixes :

- `STATIC_ROOT` devient `<racine>/staticfiles/`, ajouté au `.gitignore`. Aujourd'hui il
  pointe sur `Plantes/static`, le dossier source de l'app.
- `whitenoise.middleware.WhiteNoiseMiddleware` ajouté juste après `SecurityMiddleware`.
- Quand `DEBUG` est faux : `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`,
  `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`.
- Les clés `HOST`/`PORT`/`USER`/`PASSWORD` de `DATABASES`, inutiles pour SQLite, sont
  retirées.

### 3. `urls.py` : médias protégés

Les appels `static()` sont retirés (ils ne font rien quand `DEBUG=False`). Ils sont
remplacés par une route `media/<path:path>` vers une vue fonction `serve_media`,
décorée `login_required`, qui délègue à `django.views.static.serve` avec
`document_root=settings.MEDIA_ROOT`. Elle sert en dev comme en prod. Les statiques
sont pris en charge par whitenoise dans les deux cas.

Conséquence assumée : une image n'est plus visible sans être connecté.

### 4. `deploy/entrypoint.sh` idempotent

Exécuté à chaque démarrage du container, dans cet ordre :

1. `manage.py migrate --noinput`
2. `manage.py runscript populate_abiotic_database`
3. `manage.py runscript populate_plant_states`
4. `manage.py runscript populate_species_database`
5. `manage.py runscript link_specie_images` (voir 5)
6. `manage.py createsuperuser --noinput` seulement si les variables
   `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`
   sont définies **et** qu'aucun superuser n'existe. Sinon rien.
7. `exec` de la commande du container (uvicorn).

Tous les scripts sont déjà idempotents, un redémarrage ne crée rien en double.
Un échec d'une étape arrête le démarrage (`set -e`).

### 5. `Plantes/scripts/link_specie_images.py`

Les images d'espèces sont rangées en `media/SpecieImages/<gbif_key>/<fichier>`, le
dossier porte la clé GBIF. Le script :

- parcourt `MEDIA_ROOT/SpecieImages/*/`,
- pour chaque dossier dont le nom est une clé GBIF connue et dont l'espèce n'a pas
  d'image, prend le premier fichier du dossier et écrit le chemin relatif dans
  `Specie.image` (sans copier ni ouvrir le fichier),
- ignore les dossiers sans espèce correspondante ou vides,
- affiche le nombre d'images raccrochées.

Idempotent : une espèce qui a déjà une image n'est pas touchée. Quelqu'un sans les
fichiers de Romain lance `fetch_specie_images` à la place.

### 6. `docker-compose.yml`

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

`deploy/db/` et `deploy/media/` sont gitignorés. `deploy/entrypoint.sh` est versionné.

### 7. `.env_example` complété

Ajout de `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `PORT`, et des trois
`DJANGO_SUPERUSER_*`, avec un commentaire pour chacun. `DEBUG=False` en exemple
de prod.

### 8. README : section « Déploiement »

- Prérequis : Docker, un `.env` rempli.
- Transfert des médias depuis la machine de dev :
  `rsync -a media/ serveur:/chemin/PlantesManager/deploy/media/`
  (ou `tar` + `scp`). Optionnel : sans ça, lancer `fetch_specie_images`.
- `docker compose up -d --build`.
- Mise à jour : `git pull && docker compose up -d --build`, les migrations partent
  seules.
- Sauvegarde : copier `deploy/`.

## Gestion des erreurs

- Variable `ALLOWED_HOSTS` mal renseignée : Django renvoie 400, visible dans
  `docker compose logs`. Documenté dans le README.
- `.env` absent : compose refuse de démarrer, message explicite.
- Fichier CSV GBIF absent : `populate_species_database` échoue, l'entrypoint s'arrête.
  Le CSV est versionné, ce cas n'arrive qu'en cas de suppression volontaire.

## Tests

- `link_specie_images` : test sur base jetable (`DiscoverRunner`) avec un
  `MEDIA_ROOT` temporaire contenant deux dossiers d'espèces, un dossier inconnu et
  un dossier vide. Vérifie le raccrochage, l'idempotence, les ignorés.
- `serve_media` : test client, 302 vers login sans session, 200 avec session sur un
  fichier existant, 404 sur un fichier absent.
- Settings : `manage.py check --deploy` avec `DEBUG=False` ne remonte que les
  avertissements acceptés (HSTS, laissé au reverse proxy).
- Bout en bout, en local : `docker compose up --build` avec un `.env` de test et un
  `deploy/media/` factice de deux images. Vérifie le login, une page d'espèce avec
  image, l'accès `/media/…` refusé hors connexion. La base de dev de Romain n'est
  jamais touchée : le container écrit dans `deploy/db/`.
