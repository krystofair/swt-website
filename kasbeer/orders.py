import django.http
from django.dispatch import receiver
from django.contrib.auth import signals as auth_signals
# from django.utils.deprecation import MiddlewareMixin
# from django.core import serializers
# from aleksander.configs import RedisConfig, RedisInstance
from aleksander.clustering import RedisCache
import orjson as jsonlib
from multidict import MultiDict

import logging

from tutu import settings
from kasbeer import models

logger = logging.getLogger("OrderRepository")

#: Left for REDIS backend for repository
#: Require aleksander in version 1.4.1 (REDIS fix for working as singleton)
# class ReconfiguredRedis(RedisCache):
#   @staticmethod
#   def _get_config() -> RedisConfig:
#     return RedisConfig(broker=None, cache=RedisInstance(
#       host=settings.ORDER_REPO_REDIS_CACHE_HOST,
#       port=settings.ORDER_REPO_REDIS_CACHE_PORT
#     ))


class OrderRepository:
  """Order Repository backend for Middleware."""

  storage = dict()

  @classmethod
  def add(cls, order, user):
    """Store order for user."""
    cls.storage[user.username] = order

  @classmethod
  def remove(cls, user):
    try:
      del cls.storage[user.username]
    except KeyError:
      pass

  @classmethod
  def get(cls, user):
    """Get current order for user or None."""
    return cls.storage.get(user.username)


class OrderRepositoryMiddleware:
  """
    This middleware will associate logged user with order they have in session.
    Using REDIS for caching those is for normal expiration like sessions.
    But sessions are not yet implemented with using cache as a backend.
  """
  async_capable = False
  sync_capable = True

  def __init__(self, get_response):
    """Init in middleware is invoking once."""
    self.repo = OrderRepository
    # self.cache = ReconfiguredRedis.instance()
    self.get_response = get_response

  def __call__(self, request: django.http.HttpRequest):
    if request.user.is_authenticated:
      order = self.repo.get(request.user)
      if order is None:
        self.repo.add(models.Order(draft=False), request.user)
      request.kasbeer_order = self.repo.get(request.user)
    return self.get_response(request)

  @staticmethod
  @receiver(auth_signals.user_logged_out)
  def remove_order_for_user_after_logged_out(sender, **kwargs):
    """This will remove order from storage when user logged out."""
    logger.debug("Remove order from repository, because of user logged out.")
    OrderRepository.remove(kwargs.get('user'))


# class OrderRepositoryRedisBacked:
#   """
#     Prototype to redis as backend for order repository.
#     Was WIP, but design changed for now. 80/20. ;)
#   """
#
#   def remove(self, request):
#     keys = self._get_key_pack(request)
#     self.cache.delete(keys)
#
#   def add(self, request, order):
#     """
#       Add order to repository associated with session and user.
#       User is got from request object.
#     """
#     if request.user.is_authenticated():
#       raise ValueError("User has to be authenticated to save order for him.")
#     matches = serializers.serialize('json', order.matches)
#     jobs = serializers.serialize('json', order.jobs)
#     ord = serializers.serialize('json', [order])
#     match_key, job_key, ord_key = self._get_key_pack(request)
#     ttl = request.session.expire_date - datetime.now()
#     self.cache.setex(match_key, ttl, matches)
#     self.cache.setex(job_key, ttl, jobs)
#     self.cache.setex(ord_key, ttl, ord)
#
#   def _get_key_pack(self, request):
#     match_key = self.make_key(request, 'Match')
#     job_key = self.make_key(request, 'Job')
#     ord_key = self.make_key(request, 'Order')
#     return [match_key, job_key, ord_key]
#
#   def make_key(self, request, typename):
#     """Create key to retrieve order from cache for user and his session."""
#     username = request.user.username
#     session = request.session.session_key
#     return f"User({username}).{typename}({session})"


