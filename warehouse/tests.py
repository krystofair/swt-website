from django.test import TestCase

import sqlalchemy as sa
from datetime import datetime as dt
import unittest
from typing import Mapping

import attrs
from aleksander import dblayer
from . import views, models
# Create your tests here.


class TC(unittest.TestCase):
  def test_get_statistics(self):
    matches = ['123123', '123133', '478374']
    views.Stats.stats(['corners', 'yellows'], matches)
    
  def test_list_matches_by_team(self):
    matches_of_liverpool = list(views.Matches.by_team('liverpool'))
    if matches_of_liverpool:
      assert isinstance(matches_of_liverpool[0], Mapping), type(matches_of_liverpool[0])
    
  def test_list_leagues_api(self):
    leagues_of_england = views.Names.list_leagues('england')
    print(f"{leagues_of_england=}")
    assert 'premier-league' in set(leagues_of_england) and 'championship' in set(leagues_of_england)
    
  def test_db_connection(self):
    self.mgr = dblayer.DbMgr('sqlite')
    try:
      dblayer.Match.__table__.create(self.mgr.engine)
      dblayer.Statistic.__table__.create(self.mgr.engine)
      with sa.orm.Session(self.mgr.engine) as session:
        match = dblayer.Match(**dict(
                match_id = '123123',
                home = "mufc",
                away = 'chelsea',
                when = dt.fromisoformat('2025-02-02 18:00'),
                country = 'england',
                stadium = 'idk',
                home_score = 2,
                away_score = 2,
                referee = 'some guy',
                league = 'premier-league',
                season = '24/25'
                ))
        session.add(match)
        session.commit()
    except Exception as e:
      print('Tables exists')
      print(e)      
    with sa.orm.Session(self.mgr.eng) as ses:
      #query = sa.select(dblayer.Match).where(dblayer.Match.home.in_(['mufc']))
      query = sa.select(dblayer.Match)
      rows = ses.scalars(query)
      for r in rows:
        print('===============')
        print(f"{r.home=}")
        print(f"{r.away=}")
        print(f"{r.home_score=}")
        print(f"{r.away_score=}")

  