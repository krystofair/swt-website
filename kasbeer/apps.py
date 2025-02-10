from django.apps import AppConfig

class KasbeerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kasbeer'

    def process_new_order(self, sender, **kwargs):
        self.engine.enqueue(sender)

    def ready(self):
        from .services import Engine
        from .signals import new_order
        self.engine = Engine()
        new_order.connect(self.process_new_order)
