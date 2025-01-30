from django.dispatch import receiver
import pandas

import queue
import threading
import logging
try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

from . import models, signals


class MatchService:
  """
      Application Service to transform Orders app matches to Analyses app.
      And others utility tools with them.
  """

  @staticmethod
  def get_ids(matches):
    return [m.match_id for m in matches]


class Engine:
  """Orders Processing Service"""
  def __init__(self):
    self.orders_que = queue.Queue()
    self.orders_processing_thread = threading.Thread(target=self.__orders_processing, daemon=True)
    self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")

  def enqueue(self, order):
    """Function to enqueuing orders, used by signal dispatcher where new_order was created."""
    try:
      #: Don't process drafts.
      if order.draft:
        return
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
        self.log.debug("order thread started")
        process_order_thread.join(timeout=TIMEOUT)  # two minute is enough for single order?
        # PROPOSAL: maybe wait some time for probability of taken new order in this time,
        #           so this wont quit from this thread.
    except TimeoutError:
      self.log.error(f"Processing order {self.order!r} last over {TIMEOUT}s.")
    self.log.debug("orders processing ended")

  def __process_order(self):
    results = 0
    #: get order from queue
    order = self.orders_que.get()
    self.log.debug("PROCESS SINGLE ORDER STARTED")
    self.log.debug(f"{order.job_set.all()=}")
    
    for job in order.job_set.all():
      #: search reference analysis by name
      analysis = job.analysis()
      try:
        self.log.debug(f"{order=}, {analysis=}")
        self.log.debug(models.Analysis.objects.all())
        #: WARNING! If this can be run by specific user? Where the user object coming from?  - from order see orders.models
        task = analysis.task()
        #task.delay() # XXX: this will be in power when use celery.
        df: "pandas.DataFrame" = task(list(order.match_set.all()))
        results += 1
        job.df = df
        self.log.debug(job.df)
        job.save()
        self.log.debug(f"{job.result=}")
        #signals.analysis_complete.send(analysis.copy())
      except models.Analysis.DoesNotExist:
        self.log.warning("User choose analysis which wasn't add by admin.")
      except Exception as e:
        self.log.exception(e)
        # TODO: notify Admin.
        r = jsonlib.dumps(dict(error=str(e)))
    #: TODO: results =/= len(order.analyses) should be passed to signal?
    #signals.order_complete.send(order)
    order.complete = True
    order.save()
    self.log.debug("PROCESS SINGLE ORDER ENDED")
