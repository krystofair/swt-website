"""Entry point for loading apps and do configuration in django"""

from django.apps import AppConfig

import queue
import threading
import logging
try:
    import orjson as jsonlib
except ModuleNotFoundError:
    import json as jsonlib


class AnalysesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyses'
    engine = None
    def ready(self):
        import orders.signals as orders_signals
        from . import models        
        engine = Engine()
        orders_signals.new_order.connect(engine.enqueue)

class Engine:
    def __init__(self):
        self.orders_que = queue.Queue()
        self.process_order_thread = threading.Thread(target=self.__process_order)
        self.log = logging.getLogger("analyses.Engine")

    def enqueue(self, sender, **kwargs):
        """Function to enqueuing orders, used by signal dispatcher where new_order was created."""
        try:
            order = sender if 'order' not in kwargs else kwargs['order']
            self.orders_que.put(order)
            self.__orders_processing()
        except KeyError:
            self.log.error(f"Did not enqueue order, because there is no order. Receive those: {kwargs=}")
        
    def __orders_processing(self):
        """Processing orders one by one, by single thread until queue will be empty."""
        TIMEOUT = 120.0  # in seconds
        try:
            while not self.orders_que.empty():
                self.process_order_thread.start()
                self.process_order_thread.join(timeout=TIMEOUT)  # two minute is enough for single order?
        except TimeoutError:
            log.error(f"Processing order {self.order!r} last over {TIMEOUT}s.")
            
    def __process_order(self):
        results = 0
        #: get order from queue
        order = self.orders_que.get()
        for o_analysis in order.analyses:
            #: search reference analysis by name
            a_analysis = models.Analysis.objects.get(o_analysis.name)
            #: WARNING! If this can be run by specific user? Where the user object coming from?  - from order see orders.models
            task = a_analysis.find_task()
            #task.delay() # XXX: this will be in power when use celery.
            order_matches = [models.OrderMatchService.create_from(m) for m in order.matches]
            try:
                r = task(order_matches)
            except Exception as e:
                log.exception(e)
                r = jsonlib.dumps(dict(error=str(e)))
            results += 1
            analysis_complete.send(self, order_analysis=o_analysis, result=r)
        order_complete.send(self, order=order)

