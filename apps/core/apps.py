from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core FasoBazar'

    def ready(self):
        # On retire l'appel au seed_demo_data d'ici 
        pass
