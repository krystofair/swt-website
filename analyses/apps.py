"""Entry point for loading apps and do configuration in django"""

from django.apps import AppConfig


class AnalysesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyses'
    def ready(self):
        pass