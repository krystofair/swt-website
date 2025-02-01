import queue
import threading
import logging
try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

from . import models, signals


class OrderMatchService:
  """
      Application Service to transform Orders app matches to Analyses app.
      And others utility tools with them.
  """
  @classmethod
  def create_from(cls, orders_match):
    return cls.__mapping_order_match(orders_match)

  @staticmethod
  def __mapping_order_match(match) -> models.OrderMatch:
    """This is from DDD pattern, mapping one model from another context to this context."""
    try:
      order_match = models.OrderMatch(match.identifier, match.weight)
      return order_match
    except AttributeError:
      raise TypeError(f"Object {type(match)} is not type of Match from orders app.")

  @staticmethod
  def get_ids(matches: list[models.OrderMatch]):
    return [m.match_id for m in matches]


class Engine:
  def __init__(self):
    self.orders_que = queue.Queue()
    self.orders_processing_thread = threading.Thread(target=self.__orders_processing, daemon=True)
    self.log = logging.getLogger("analyses.Engine")

  def enqueue(self, sender, **kwargs):
    """Function to enqueuing orders, used by signal dispatcher where new_order was created."""
    try:
      order = sender if 'order' not in kwargs else kwargs['order']
      self.orders_que.put(order)
      if not self.orders_processing_thread.is_alive():
        self.orders_processing_thread.start()
    except KeyError:
      # never raised.
      self.log.error(f"Did not enqueue order, because there is no order. Receive those: {kwargs=}")

  def __orders_processing(self):
    """Processing orders one by one, by single thread until queue will be empty."""
    TIMEOUT = 120.0  # in seconds
    process_order_thread = threading.Thread(target=self.__process_order)
    self.log.debug("orders processing started")
    try:
      while not self.orders_que.empty():
        process_order_thread.start()
        process_order_thread.join(timeout=TIMEOUT)  # two minute is enough for single order?
        # PROPOSAL: maybe wait some time for probability of taken new order in this time,
        #           so this wont quit from this thread.
    except TimeoutError:
      self.log.error(f"Processing order {self.order!r} last over {TIMEOUT}s.")

  def __process_order(self):
    results = 0
    #: get order from queue
    order = self.orders_que.get()
    analyses = order.analyses
    for o_analysis in analyses:
      #: search reference analysis by name
      try:
        self.log.debug(f"{order=}, {o_analysis=}")
        self.log.debug(models.Analysis.objects.all())
        a_analysis = models.Analysis.objects.get(name = o_analysis.name)
        #: WARNING! If this can be run by specific user? Where the user object coming from?  - from order see orders.models
        task = a_analysis.find_task()
        #task.delay() # XXX: this will be in power when use celery.
        order_matches = [OrderMatchService.create_from(m) for m in order.matches]
        df: "pandas.DataFrame" = task(order_matches)
        results += 1
        result = models.Result(dataframe=df, analysis=a_analysis)
        result.save()
        #signals.analysis_complete.send(a_analysis)
      except models.Analysis.DoesNotExist:
        self.log.warning("User choose analysis which wasn't add by admin.")
      except Exception as e:
        self.log.exception(e)
        # TODO: notify Admin.
        r = jsonlib.dumps(dict(error=str(e)))
    #: results =/= len(order.analyses) should be passed to signal?
    #signals.order_complete.send(order)
    order.complete = True
    order.save()
