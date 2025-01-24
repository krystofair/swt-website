"""
    Store models of analyses here.
"""
import pandas as pd


class StatAnalysis:
  """
      Analysis task to do. This will calculate simple nothing.
      I mean some tested DataFrame will be created, so it is nothing.
  """

  def __init__(self, order):
    """Arguments:
        o: reference to object of order, as observer pattern.
    """
    self.o = order
    
  def calculate(self, matches):
    """Calculation of this analysis"""
    print("check out")
    return pd.DataFrame
  
  def run(self, *args, **kwargs):
    """Endpoint to invoke by multiprocessing module."""
    result = self.calculate(*args, **kwargs)
    order.send(self, result)
  
  def execute(self):
    try:
      result = self.calculate(matches)
    except Exception as e:
      log.error(e)
    else:
      self.order.send(self)