from django.db import models
from django.contrib.auth.models import User
import pandas
import attrs

import importlib



# Create your models here.


ANALYSES_MODULE = 'analyses.tasks'

def collect_tasks() -> list[dict]:
  names: list[dict] = list()
  mtasks = importlib.import_module(ANALYSES_MODULE)
  for f in mtasks.__dict__:
    prop = getattr(mtasks, f)
    if hasattr(prop, '__analysis_name__'):
      names.append(dict(
        name = prop.__analysis_name__,
        task_func = prop.__qualname__,
        description = prop.__doc__
      ))
  return names

def prepare_choices_tasks(tasks: list[dict]):
  yield from ((t['name'], t['task_func']) for t in tasks)

class Analysis(models.Model):
  """
      Model for managing analyses, because of they are functions,
      here is task_func_name as a choice.
      TODO: Refactoring this model, much.
  """
  # this is automatically set up from function in tasks module because of decorator there.
  name = models.CharField(primary_key=True, max_length=128)
  task_func = models.CharField(max_length=128, choices=prepare_choices_tasks(collect_tasks()))
  # description = models.TextField()

  def save(self, **kwargs):
    """Save Analysis with automatically setting name to it"""
    try:
      t = self.find_task()
      self.name = t.__analysis_name__
      super().save(**kwargs)
    except:
      raise
      
  
  def find_task(self):
    """Returns function from python code as code. This task could be called."""
    tasks = importlib.import_module(ANALYSES_MODULE)
    if hasattr(tasks, self.task_func):
      return getattr(tasks, self.task_func)
    raise ValueError("This analysis has not implementation or name of function `task_func` is wrong.")


@attrs.define
class OrderMatch:
  match_id: str
  weight: float

class Result(models.Model):
  analysis = models.OneToOneField(Analysis, on_delete=models.CASCADE)
  #: State, for now it is just JSON, features - protobuf.
  dataframe = models.JSONField()
  
  def df(self) -> pandas.DataFrame:
    return pandas.DataFrame.from_dict(jsonlib.loads(self.dataframe))
    
  def save(self, **kwargs):
    if isinstance(self.dataframe, pd.DataFrame):
      self.dataframe = self.dataframe.to_json()
    super(Result, self).save(**kwargs)
  
