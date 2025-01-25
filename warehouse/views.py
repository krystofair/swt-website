from django.shortcuts import render
from django.apps import apps


import sqlalchemy as sa
from aleksander.dblayer import *
from collections import namedtuple
import pandas as pd

from . import models
import logging
log = logging.getLogger(__name__)

# Create your views here.
# This is views, but in database perspective :)

#: reference to config of this application.
wh = apps.get_app_config('warehouse')
def _log_query(q):
  """logging query for test phase, with format to nice parsing by markdown editors."""
  log.info(f"""```sql
           {q}
           ```""")

class API:

  @staticmethod
  def _exe_query(q):
    """Execute query helper, for focus on writing queries in below methods."""
    try:
      #: Special logging of query
      _log_query(q)
      with sa.orm.Session(wh.dbmgr.eng) as s:
        return [r._mapping for r in s.execute(q).all()]
    except Exception as e:
      log.exception(e)
      raise
    return []

class Matches(API):
  """API of returning match listing"""
  
  #: aliases for results
  SimpleMatch = (Match.home, Match.away, Match.home_score, Match.away_score)
      
  @staticmethod
  def by_team(team):
    """ listing all matches which team played"""
    query = (sa.select(*Matches.SimpleMatch)
             .where(Match.home == team or Match.away == team))
    matches = list()
    try:
      with sa.orm.Session(wh.dbmgr.eng) as session:
        for row in session.execute(query).all():
          matches.append(row._mapping)
    except Exception as e:
      log.exception(e)
    return matches
  
  @classmethod
  def by_team_winner(cls, team):
    q = sa.select(*cls.SimpleMatch).where(
      (Match.home == team and Match.home_score > Match.away_score)
      or
      (Match.away == team and Match.away_score > Match.home_score)
    )
    return API._exe_query(q)
  
  @classmethod
  def by_tournament(cls, tournament):
    """list matches by league + country (I named it as tournament)"""
    league, country = tournament
    q = sa.select(*cls.SimpleMatch).where(
      Match.league == league and Match.country == country)
    return API._exe_query(q)
  
  @classmethod
  def by_season_of_tournament(cls, season, tournament):
    """name explain everything"""
    return NotImplemented
  
  @classmethod
  def by_team_in_tournament(cls, team, tournament):
    league, country = tournament
    q = sa.select(*cls.SimpleMatch).where(
      (Match.home == team or Match.away == team)
      and (Match.league == league and Match.country == country)
    )
    return API._exe_query(q)
  

class Names(API):
  """
      Names - API for selecting sets of names like league, countries, things which are stored in 'DataDB'.
      DataDB - database with matches and objects related to them.
  """
    
  @staticmethod
  def list_leagues(country):
    """listing leagues by country, without country leagues are not listed."""
    query = sa.select(Match.league.distinct()).where(Match.country == country)
    try:
      with sa.orm.Session(wh.dbmgr.eng) as session:
        return list(map(str, session.scalars(query)))
    except Exception as e:
      log.exception(e)
      return []
  
  @staticmethod
  def list_countries():
    """listing all countries from database for matches"""
    query = sa.select(Match.country.distinct())
    try:
      with sa.orm.Session(wh.dbmgr.eng) as session:
        return list(map(str, session.scalars(query)))
    except Exception as e:
      log.exception(e)
      return []
  
  @staticmethod
  def list_seasons_for_tournament(tournament: models.Tournament|tuple[str, str]):
    league, country = tournament
    """seasons only per league"""
    query = sa.select(Match.season.distinct()).where(Match.league == league and Match.country == country)
    try:
      with sa.orm.Session(wh.dbmgr.eng) as session:
        return list(map(str, session.scalars(query)))
    except Exception as e:
      log.exception(e)
      return []


class Stats(API):
  """
      Stats returning views defined below like `BasicView`,
      but in the most cases changing them into pandas DataFrames additionally.
  """
  BasicView = (Statistic.name, Statistic.home, Statistic.away)
  
  @classmethod
  def stats(cls, names, matches):
    """
        Returning pandas dataframe~s~ for passed statistic names.
        ~So query is for all names, but then this grouping it for list by names.~
        Arguments:
          names - names of statistics to collect,
          matches - object of matches with attribute match_id or simple list of ids in string.
    """
    ids = []
    try:
      ids = [m.id for m in matches]
    except AttributeError:
      ids = matches
    if not ids:
      raise ValueError("Cannot get statistics, because of condition")
    query = (sa.select(*cls.BasicView, Match.match_id).where(Statistic.name.in_(names))
             .join(Match).where(Match.match_id.in_(ids)))
    result_t_mappings = API._exe_query(query)
    single_frame = pd.DataFrame(result_t_mappings)
    log.debug(single_frame)
    #single_frame.groupby(['name'])
    return single_frame

  
