from django.shortcuts import render
from django.apps import apps
import sqlalchemy as sa
# TODO: set explicit models from aleksander.
from aleksander.dblayer import *

import typing
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
  SimpleMatch = (Match.match_id, Match.home, Match.away, Match.home_score,
                 Match.away_score, Match.when)
  LeagueMatch = (*SimpleMatch, Match.league)

  def __init__(self, display_set=None):
    self.display_set = display_set or Matches.SimpleMatch

  def by_ids(self, mids):
    """ Simple retrieve match or matches (in Simple format) from DB by its identifier."""
    log.debug(mids)
    query = sa.select(*self.display_set).where(Match.match_id.in_(mids))
    return API._exe_query(query)

  def by_team(self, team):
    """ listing all matches which team played"""
    team = sa.or_(Match.home.like(f"%{team}%"), Match.away.like(f"%{team}%"))
    query = sa.select(*self.display_set).where(team)
    return API._exe_query(query)

  def by_team_winner(self, team):
    #: where conditions
    home_winner = sa.and_(Match.home == team, Match.home_score > Match.away_score)
    away_winner = sa.and_(Match.away == team, Match.away_score > Match.home_score)
    #: query
    q = sa.select(*self.display_set).where(sa.or_(home_winner, away_winner))
    return API._exe_query(q)

  def by_tournament(self, tournament: models.Tournament):
    """list matches by league + country (I named it as tournament)"""
    league, country = tournament
    log.debug(f"{league=}, {country=}, {tournament=}")
    q = sa.select(*self.display_set).where(sa.and_(Match.league == league, Match.country == country))
    return API._exe_query(q)

  def by_season_of_tournament(self, season, tournament):
    """name explain everything"""
    return []

  def by_team_in_tournament(self, team, tournament):
    league, country = tournament
    #: conditions
    team = sa.or_(Match.home == team, Match.away == team)
    league_and_country = sa.and_(Match.league == league, Match.country == country)
    team_and_tournament = sa.and_(team, league_and_country)
    q = sa.select(*self.display_set).where(team_and_tournament)
    return API._exe_query(q)
  

class Names(API):
  """
      Names - API for selecting sets of names like league, countries, things which are stored in 'DataDB'.
      DataDB - database with matches and objects related to them.
  """
    
  @staticmethod
  def list_leagues(country):
    """listing leagues by country, without country leagues are not listed."""
    log.debug(f"list_leagues({country=})")
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
    log.debug(f"list_seasons_for_tournament({league=}, {country=},"
              f" {tournament=})")
    """seasons only per league"""
    query = sa.select(Match.season.distinct()).where(
      sa.and_(Match.league == league, Match.country == country))
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
        Returning pandas dataframe for passed statistic names.
        Arguments:
          names: names of statistics to collect,
          matches: matches as kasbeer.Match or string of ids
    """
    errors = []  # this is a list to validation data output. This will be upgraded in future.
    # I just point it out here for a moment.
    ids = []
    try:
      ids = [m.identifier for m in matches]
    except AttributeError:
      ids = matches
    # TODO: here not necessary is this JOIN for matches,
    #       match_id exists in staistics table too.
    query = (sa.select(*cls.BasicView, Match.match_id)
             .distinct(Statistic.match_id, Statistic.name)
             .where(Statistic.name.in_(names))
             .join(Match).where(Match.match_id.in_(ids)))
    result_t_mappings = API._exe_query(query)
    if len(result_t_mappings) < len(ids):
      results_ids = [r.match_id for r in result_t_mappings]
      lack_of_set = set(ids).difference(set(results_ids))
      errors.append("There is no stats for {} matches: {}"
        .format( len(ids) - len(result_t_mappings), ','.join(lack_of_set))
      )
    single_frame = pd.DataFrame(result_t_mappings)
    single_frame = single_frame.drop_duplicates(subset='match_id')
    log.debug(single_frame)
    #single_frame.groupby(['name'])
    return single_frame, errors

  
