"""Entry point for loading apps and do configuration in django"""

from django.apps import AppConfig


class AnalysesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyses'
    engine = None
    def ready(self):
        import orders.signals as orders_signals
        from . import models, services
        engine = services.Engine()
        orders_signals.new_order.connect(engine.enqueue)

