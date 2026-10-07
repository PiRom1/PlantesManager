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
