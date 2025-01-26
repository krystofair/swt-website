"""
    Set of function which converting data to meanings. The __doc__ of function is for description in model.Analysis.
"""
import pandas as pd

import warehouse.views as wh

# todo: learning i18 in Django.


def set_name(friendly_name):
  """
      Setting name for analysis model by decorator it is for be visiable nicely when Admin will add permission.
  """
  def wrapper(f):
    f.__analysis_name__ = friendly_name
    return f
  return wrapper


@set_name("Analiza rzutów rożnych 1")
def analyse_corners_line_auto(match_ids: list[str]):
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
      Znowu mam wrażenie, że to się w ogóle nie opłaca. W sensie takie pojedyncze akcje.
  """
  frame = wh.Stats.stats('ball-possession', matches)
  aleksy_models_match = wh.Match
  if not isinstance(matches[0], aleksy_models_match):
    ms = wh.Matches.by_ids(matches)
  # pd.correlate(frame, ms) # XD
  return 0  # brak korelacji XD

@set_name("Szukanie korelacji pomiędzy statystykami")
def oblicz_korelacje_statystyk_kazdy_z_kazdym(ms):
  """
      I coś takiego będzie się dało już na wykresie wyświetlić.
      Będziemy mieli punkty dla każdej korelacji, których będzie duużo w zakresie -1 do 1.
      Gdzie korelacja będzie liniowa Pearsona.
      Jak nie podłączę tutaj KNIMEa to nie ma ciekawych rzeczy tutaj. Szczególnie gdy na każdą rzecz muszę napisać
      nową funkcję. Ale przesadzam, bo przecież w jednej analizie mogę stworzyć wiele dataframe'ów i napisać do tego
      widok jaki chcę. Nic mnie nie ogranicza.
  """
  pass

