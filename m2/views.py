"""
    API for do research stuff.
"""

from .apps import M2Config as m2_app
# Create your views here.

def visual(request):
  """zwróć właściwie co?"""

def weight(match_id):
  """This should have a lot cache logic to not start from scratch every time."""
  return 1.0
  
def plan(order):
  """Plan order to processing."""
  m2_app.engine.enqueue(order)
