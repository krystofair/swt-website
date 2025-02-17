"""
    Set of function which converting data to meanings. The __doc__ of function is for description in model.Analysis.
"""
from django.contrib import admin
from django.utils.text import slugify
import pandas as pd
import numpy as np

import importlib
import logging
from datetime import datetime

import warehouse.views as wh
from tutu import settings


ANALYSES_MODULE = 'm2.tasks'

logging.basicConfig()
log = logging.getLogger("AnalysisTasks")
# TODO: Interesting subject to analyse code by decorator and change calling
#       some function with another (thinking about log, to logger name change)

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


#%% Temporary some utils to save analysis into file.
#%%

# def save_result_to_file(f, path=""):
#   logging.basicConfig(filename="results_of_analyses.csv", format="%(analysis_name)s,%(generation_time)s,%(json_result)s")
#   log = logging.getLogger(f.__analysis_name__)
#   log
#   def wrapper(*args, **kwargs):
#     generation_time = datetime.now().isoformat(sep='@', timespec="milliseconds")
#     result = f(*args, **kwargs)
#
#     result.to_json()
#   return wrapper


@set_name("Test dodawania analizy")
def test_add_analysis_choices(matches):
  return test_task(matches)

@set_name("Testowa analiza")
def test_task(matches):
  cols = pd.Index(list['abcd'])
  df = pd.DataFrame([1,2,3,4], [5,6,7,8], columns=cols)
  return df


def common_to_stat_analyses(stats_list, matches):
  #: List of needed stasts
  list_of_stats = stats_list
  #: API call for statistics
  stats_df, errors = wh.Stats.stats(list_of_stats, matches)
  now = format(datetime.now(), "[%d-%m-%Y @ %H:%M:%S.%Z]")
  for error in errors:
    with open(f"/d/analityk/abuilda/abuilda/logs/error.log", 'a',
              encoding='utf-8') as error_log:
      print(f"{now} {error}", file=error_log)
    # log.warning(error)
  #: Build frame from chosen matches
  matches_df = pd.DataFrame([{'match_id': m.identifier, 'weight': m.weight}
                             for m in matches])
  #: merge to one frame by compare match_id, with how='outer' to has indicator
  #  well worked
  pframe = pd.merge(matches_df, stats_df, on='match_id', copy=False,
                    indicator=True, how='outer')
  delta = (pframe._merge != 'both').sum()
  log.debug('DELTA IS {}'.format(delta))
  # if delta/len(matches) > 0.45:
  #   raise ValueError("TooSmallDataset(delta={})".format(delta))
  # log errors, cause in analysis there is no place for errors yet.
  #: filtered out if not both.
  return (
    pframe[pframe._merge == 'both']
    .drop(['_merge'], axis=1)  # drop indicator.
    .reset_index(drop=True)
  )


def lines_analysis(pframe):
  # %% badanie linii z ramki pframe
  lines = np.arange(0.5, 25.5, 1)
  #: Prepare new dataframe for this research
  over = pd.DataFrame()
  #: Index of this dataframe is all columns to calculate from data
  over.index = pframe.columns
  nom = len(pframe.index)  # number of matches = length data index
  under = over.copy()
  for line in lines:
    over[str(line)] = (pframe > line).sum()
    under[str(line)] = nom - over[str(line)]
  # clear non important lines
  over = over.loc[:, (over != 0).any(axis=0)].loc[:, (over < 1).any(axis=0)]
  under = under.loc[:, (under != 1).any(axis=0)].loc[:, (under > 0).any(axis=0)]
  return {
    'over': over * 100,
    'under': under * 100
  }

@set_name("Analiza rzutów rożnych 1")
def analyse_corners_line_auto(matches):
  """
      Wyliczanie sensu ryzyka dla linii w statystyce rzutów rożnych.
      Im mniejsza odległość między liniami tym bardziej warto zagrać wg Twojego ważenia meczów!
      Wagi mają znaczenie że przykładowo na 10 meczów 5 jest over linii 3.5, ale tych 5 meczów jest wagowo słabe,
      więc inna wyższa linia może być tylko niewiele oddalona od 3.5 co oznacza że warto zagrać tę wyższą.
  """
  try:
    # , 'yellow-cards', 'shots-on-target', 'shots-off-target']
    pframe = common_to_stat_analyses(['corner-kicks'], matches)
    return pframe
  except Exception as e:
    # TODO: Raise error to be saved in errors (upframe).
    log.exception(e)
    return pd.DataFrame()


@set_name("Rzuty rożne describe dla Boxa")
def corners_box_describe_totals(matches):
  """Soon or later there will be for specific teams too."""
  try:
    pframe = common_to_stat_analyses(['corner-kicks'], matches)
    pframe['total'] = pframe['home'] + pframe['away']
    pframe = pframe.drop(['home', 'away', 'name', 'match_id'], axis=1)
    describe_df = pframe[['total']].describe()
    return describe_df
  except Exception as e:
    log.exception(e)
    return pd.DataFrame()

@set_name("Analiza rzutów rożnych 2.0")
def analyse_corners_2(matches):
  """
  Wyznacza zmiany wag pomiędzy kolejnymi liniami, i fajnie by było gdyby
  kolorował je w zależności zmiany wagi over -> under, lub under -> over.
  Aczkolwiek to chyba zawsze tak samo wyjdzie - uwidzimy.
  """
  try:
    # home | away | match_id | name | weight
    # ale drop'uję te match_id i name , więc mamy
    # home | away | weight
    pframe = common_to_stat_analyses(['corner-kicks'], matches)
    #: create sum from home and away
    pframe['total'] = pframe['home'] + pframe['away']
    pframe = pframe.drop(['home', 'away', 'name', 'match_id'], axis=1)

    ### badanie linii z ramki pframe
    lines = np.arange(0.5, 25.5, 1)
    over = pd.DataFrame()
    under = over.copy()

    for line in lines:
      over[str(line)] = pframe.loc[pframe['total'] > line, ['weight']].sum()
      under[str(line)] = pframe.loc[pframe['total'] < line, ['weight']].sum()

    over = over.rename({'weight': 'weight_over'})
    under = under.rename({'weight': 'weight_under'})
    total_weight = pframe['weight'].sum()
    ou = pd.concat([over, under], axis=0)
    ou.loc['weight_under', :] = ou.loc['weight_under', :].shift(-1)
    ou.loc['diff_sign', :] = ou.loc['weight_over', :] - ou.loc['weight_under', :]
    ou.loc['diff_abs', :] = ou.loc['diff_sign', :].abs()
    ou = ou.loc[:, ou.loc['diff_abs', :] < total_weight]
    log.info(ou)
    return ou
  except Exception as e:
    log.exception(e)
    return pd.DataFrame()

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

