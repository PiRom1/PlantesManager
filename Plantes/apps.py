from django.apps import AppConfig


class PlantesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Plantes'

    def ready(self):
        import Plantes.signals  # Charger les signaux  # noqa: F401
