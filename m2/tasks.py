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

def _match_as_dict(m):
  return {
    "match_id": m.identifier,
    "weight": np.float64(m.weight)
  }

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
  lack_rate = delta/len(matches)
  if lack_rate > 0.25:
    raise ValueError(
      "Cannot calculate, number of lacking stats is more than 25%.({})"
      .format(lack_rate)
    )
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
    raise


@set_name("Rzuty rożne describe dla Boxa")
def corners_box_describe_totals(matches):
  """Soon or later there will be for specific teams too."""
  try:
    pframe = common_to_stat_analyses(['corner-kicks'], matches)
    pframe['total'] = pframe['home'] + pframe['away']
    pframe = pframe.drop(['home', 'away', 'name', 'match_id'], axis=1)
    df = pframe[['total']].describe()
    mean = df.loc['mean', 'total']
    std = df.loc['std', 'total']
    df = df.drop(index=['count','mean','std'])
    df.loc['50%', 'total'] = mean
    df.loc['min', 'total'] = 1
    df.loc['max', 'total'] = 1
    df.loc['25%', 'total'] = std
    df.loc['75%', 'total'] = std
    return df
  except Exception as e:
    log.exception(e)
    raise

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
    raise

@set_name("Goals lines weighted")
def goals_lines_with_weights(matches):
  """
  Analiza lini dla ilości bramek w meczach
  """
  try:
    frame_goals_with_stats, errors = wh.Stats.stats_with_goals(['ball-possession'], matches)
    log.info(frame_goals_with_stats)
    log.error(errors)
    #: Build frame from chosen matches
    matches_df = pd.DataFrame(list(map(_match_as_dict, matches)))
    scores_frame = frame_goals_with_stats[['home_score', 'away_score', 'match_id']]
    pframe = matches_df.merge(scores_frame, on="match_id")
    ### create lines
    lines = np.arange(0.5, 25.5, 1)
    over = pd.DataFrame()
    under = over.copy()
    for line in lines:
      over[str(line)] = pframe.loc[(pframe['home_score'] + pframe['away_score']) > line, ['weight']].sum()
      under[str(line)] = pframe.loc[(pframe['home_score'] + pframe['away_score']) < line, ['weight']].sum()
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
    raise

@set_name("Yellow cards lines weighted")
def yellows_lines_weighted(matches):
  """
  Wyznacza zmiany wag pomiędzy kolejnymi liniami dla żółtych kartek.
  """
  try:
    # home | away | match_id | name | weight
    # ale drop'uję te match_id i name , więc mamy
    # home | away | weight
    pframe = common_to_stat_analyses(['yellow-cards'], matches)
    #: create sum from home and away
    pframe['total'] = pframe['home'] + pframe['away']
    pframe = pframe.drop(['home', 'away', 'name', 'match_id'], axis=1)

    ### badanie linii z ramki pframe
    lines = np.arange(0.5, 15.5, 1)
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
    raise

@set_name("Foul lines analysis weighted")
def foul_lines_weighted(matches):
  """
  Wyznacza zmiany wag pomiędzy kolejnymi liniami.
  """
  try:
    # home | away | match_id | name | weight
    # ale drop'uję te match_id i name , więc mamy
    # home | away | weight
    pframe = common_to_stat_analyses(['fouls'], matches)
    #: create sum from home and away
    pframe['total'] = pframe['home'] + pframe['away']
    pframe = pframe.drop(['home', 'away', 'name', 'match_id'], axis=1)

    ### badanie linii z ramki pframe
    lines = np.arange(5.5, 95.5, 1)
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
    raise
  
@set_name("Shots_on_target lines analysis weighted")
def shots_on_target_lines_weighted(matches):
  """
  Wyznacza zmiany wag pomiędzy kolejnymi liniami.
  """
  try:
    # home | away | match_id | name | weight
    # ale drop'uję te match_id i name , więc mamy
    # home | away | weight
    pframe = common_to_stat_analyses(['shots-on-target'], matches)
    #: create sum from home and away
    pframe['total'] = pframe['home'] + pframe['away']
    pframe = pframe.drop(['home', 'away', 'name', 'match_id'], axis=1)

    ### badanie linii z ramki pframe
    lines = np.arange(5.5, 95.5, 1)
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
    raise

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


@set_name("Korelacja współczynnika oddanych strzałów do wyniku.")
def correlation_rate_on_off_to_result(matches):
  """
      Obliczanie strzałów oddanych w światło bramki do tych przestrzelonych.
      Następnie jeśli drużyna przekroczyła wyznaczony próg - aktualnie to jest
      0.65 - oraz wygrała mecz, to zalicza się jej punkty w ilości wagi za mecz.
  """
  log.info("start task: 'correlation_rate_on_off_to_result'")
  THRESHOLD = 0.65
  #: Function for counting rates.
  def rate(x):
    a, b = x['shots-on-goal'], x['shots-off-goal']
    return a / b if b != 0 else a + 1  # plus one instead of infinity.
  try:
    #: Run common... to check delta
    frame = common_to_stat_analyses(['shots-on-goal', 'shots-off-goal'], matches)
    #: Getting statistics per match
    df, errors = wh.Stats.stats_with_goals(
      ['shots-on-goal', 'shots-off-goal'],
      matches
    )
    matches_df = pd.DataFrame(list(map(_match_as_dict, matches)))
    df = df.drop_duplicates()
    df = df.set_index('name', drop=True)
    # %% group and calculate rates
    multi_index_labels = ['match_id', 'home', 'away', 'home_score', 'away_score']
    gr = df.groupby(multi_index_labels)
    df2 = gr.agg(rate)
    df2 = df2.reset_index()
    #: Merging calculated rates, stats with weight
    mdf = matches_df.merge(df2, on='match_id')
    # %% calculate points
    stdf = mdf.loc[:, ['stat_home', 'stat_away']]
    mdf[['points_home', 'points_away']] = np.round(
      (stdf[stdf > THRESHOLD].mul(mdf['weight'], axis=0)).fillna(0),
      3
    )
    # %% calculate points
    home_points_per_team = mdf.groupby('home')['points_home'].sum()
    away_points_per_team = mdf.groupby('away')['points_away'].sum()
    #: "points" table is |team|points|
    points = home_points_per_team + away_points_per_team
    points = points.fillna(0).reset_index()
    points.columns = ['team_name', 'points']
    # XXX: Dane muszą być z jednego portalu inaczej to się rozjedzie, ponieważ drużyny będą inaczej nazywane.
    #    : Ale mam pomysł jak to rozwiązać, sukcesywnie tworzyć tabelę zespołów które są niezależne, czyli stworzę aplikację,
    #    : na wagtailu, w której będzie cała mapa dynamicznie rozwijana przez AI, żart, normalnie ludzi i do tej tabeli będą porównywane
    #    : dane spływające z portali.
    log.info("end task: 'correlation_rate_on_off_to_result'")
    log.info(f"==Produced DataFrame==\n{points}")
    return points
  except Exception as e:
    log.exception(e)
    raise

