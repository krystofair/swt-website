"""
    Set of function which converting data to meanings. The __doc__ of function is for description in model.Analysis.
"""
from django.contrib import admin
from django.utils.text import slugify
import pandas as pd

import importlib

import warehouse.views as wh


ANALYSES_MODULE = 'kasbeer.tasks'

#def analysis(name, **options):
  #def _from_fun(func):
    ##: Title all then split by space in order to join it again without spaces.
    #only_ascii_name = slugify(name)
    #class_name = ''.join(only_ascii_name.replace('-', ' ').title().split(' '))
    #analysis_new_class = type(class_name, (models.Model,), dict({
      #'name': name,
      #'task_func': func.__qualname__,
      #'db_table': "analyses",
      #'__doc__': func.__doc__,
      #'__module__': func.__module__,
      #'__annotations__': func.__annotations__
      #}, **options))()
  #return _from_fun

def collect_tasks() -> list[dict]:
  names: list[dict] = list()
  mtasks = importlib.import_module(ANALYSES_MODULE)
  for f in mtasks.__dict__:
    prop = getattr(mtasks, f)
    if hasattr(prop, '__analysis_name__'):
      names.append(dict(
        analysis = prop,
        name = prop.__analysis_name__,
        task_func = prop.__qualname__,
        description = prop.__doc__
      ))
  return names

def prepare_choices_tasks(tasks: list[dict]):
  yield from ((t['task_func'], t['name']) for t in tasks)
  
def set_name(friendly_name):
  """
  Setting name for analysis model by decorator it is for be visiable nicely when Admin will add permission.
  """
  def wrapper(f):
    f.__analysis_name__ = friendly_name
    return f
  return wrapper



@set_name("Test dodawania analizy")
def test_add_analysis_choices(matches):
  return test_task(matches)

@set_name("Testowa analiza")
def test_task(matches):
  cols = pd.Index(list['abcd'])
  df = pd.DataFrame([1,2,3,4], [5,6,7,8], columns=cols)
  return df


@set_name("Analiza rzutów rożnych 1")
def analyse_corners_line_auto(matches):
  """
      Wyliczanie sensu ryzyka dla linii w statystyce rzutów rożnych.
      Im mniejsza odległość między liniami tym bardziej warto zagrać wg Twojego ważenia meczów!
      Wagi mają znaczenie że przykładowo na 10 meczów 5 jest over linii 3.5, ale tych 5 meczów jest wagowo słabe,
      więc inna wyższa linia może być tylko niewiele oddalona od 3.5 co oznacza że warto zagrać tę wyższą.
  """
  #: pobieranie danych z api
  frame = wh.Stats.stats(['corner-kicks'], match_ids)
  Matches = wh.Matches.by_ids(match_ids)
  return frame

@set_name("Korelacja posiadania piłki do wyniku meczu")
def correlation_bp2result(matches):
  """
      Tutaj nawet nie musi być wyliczanej korelacji jako tako, choć może być, ale wynik będzie pojedynczą cyfrą.
      Chodzi tutaj raczej o takie przedstawienia danych, które będzie do nas przemawiało.
      Mam wrażenie, że to się w ogóle nie opłaca. W sensie takie pojedyncze akcje.
  """
  frame = wh.Stats.stats('ball-possession', )
  aleksy_models_match = wh.Match
  if not isinstance(matches[0], aleksy_models_match):
    ms = wh.Matches.by_ids(matches)
  # pd.correlate(frame, ms) # XD
  return 0  # brak korelacji XD

@set_name("Szukanie korelacji pomiędzy statystykami")
def oblicz_korelacje_statystyk_kazdy_z_kazdym(matches):
  """
      I coś takiego będzie się dało już na wykresie wyświetlić.
      Będziemy mieli punkty dla każdej korelacji, których będzie duużo w zakresie -1 do 1.
      Gdzie korelacja będzie liniowa Pearsona.
      Jak nie podłączę tutaj KNIMEa to nie ma ciekawych rzeczy tutaj. Szczególnie gdy na każdą rzecz muszę napisać
      nową funkcję. Ale przesadzam, bo przecież w jednej analizie mogę stworzyć wiele dataframe'ów i napisać do tego
      widok jaki chcę. Nic mnie nie ogranicza.
  """
  pass

