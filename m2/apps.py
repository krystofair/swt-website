"""Entry point for loading apps and do configuration in django"""

from django.apps import AppConfig


class M2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'm2'
    engine = None
    def ready(self):
        from .services import Engine
        self.__class__.engine = Engine()
