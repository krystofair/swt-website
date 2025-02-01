from django.forms import ModelChoiceField
from django.forms.models import ModelChoiceIterator
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import JsonResponse
from django import forms
from django.utils import choices
import orjson as jsonlib

import functools

#: API for names .
import warehouse.views as wh


class FilterLogic:
    """Logic of filtering."""

    def post(self, request, *args, **kwargs):
        r = request
        #: here is a reassignment requirement
        ctx = dict()
        ctx |= r.session.get('state', dict())
        team = r.POST.get('team', None)
        league = r.POST.get('league', None)
        country = r.POST.get('country', None)
        season = r.POST.get('season', None)
        log.debug(f"post parameters {team=}, {league=}, {country=}, {season=}")
        if team:
            if not all([league, country]):
                ctx.update(filtermatches=wh.Matches.by_team(team))
            else:
                if league and country:
                    tournament = (league, country)
                    ctx.update(filtermatches=wh.Matches.by_team_in_tournament(team, tournament),
                               seasons_from_leagues=wh.Names.list_seasons_for_tournament(tournament))
        else:
            tournament = (league, country)
            if all([country, league, season]):
                ctx.update(filtermatches=wh.Matches.by_season_of_tournament(season, tournament),
                           seasons_from_leagues=wh.Names.list_seasons_for_tournament(tournament))
            elif country and league:
                ctx.update(filtermatches=wh.Matches.by_tournament(tournament),
                           seasons_from_leagues=wh.Names.list_seasons_for_tournament(tournament))
            elif country and not all([league, season]):
                ctx.update(filterleagues=wh.Names.list_leagues(country))
        log.debug(f"{ctx=}")
        # r.session['state'] = ctx
        return render(request, self.template_name, context=ctx)

class FilteringForm(forms.Form):

    team = forms.CharField(required=False)
    country = forms.ChoiceField(choices=[(c, c.title()) for c in wh.Names.list_countries()])
    league = forms.ChoiceField(choices=choices.CallableChoiceIterator(functools.partial(wh.Names.list_leagues,
                                                                                        country)))
    season = forms.ChoiceField(choices=choices.CallableChoiceIterator(functools.partial(
        wh.Names.list_seasons_for_tournament, (league, country))))

    def __init__(self, *args, **kwargs):
        self.matches = []
        data = args[0] if len(args) >= 1 else None
        if not data:
            countries = wh.Names.list_countries()
            leagues = wh.Names.list_leagues(countries[0])
            seasons = wh.Names.list_seasons_for_tournament((leagues[0], countries[0]))
            # data = {
            #     'countries': [(c, c.title()) for c in countries],
            #     'leagues': [(l, l.title()) for l in leagues],
            #     'seasons': [(s, s.title()) for s in seasons]
            # }
            data = {
                'countries': countries[0],
                'leagues': leagues[0],
                'seasons': seasons[0]
            }
        super().__init__(data)

    def get_context(self):
        team = self.data.get('team', None)
        league = self.data.get('leagues', None)
        country = self.data.get('countries', None)
        season = self.data.get('seasons', None)
        if team:
            if not all([league, country]):
                self.matches = wh.Matches.by_team(team)
            else:
                if league and country:
                    tournament = (league, country)
                    self.matches = wh.Matches.by_team_in_tournament(team, tournament)
                    self.season = wh.Names.list_seasons_for_tournament(tournament)
        else:
            tournament = (league, country)
            if all([country, league, season]):
                self.season = wh.Names.list_seasons_for_tournament(tournament)
                self.matches = wh.Matches.by_season_of_tournament(season, tournament)
            elif country and league:
                self.matches = wh.Matches.by_tournament(tournament)
                self.season = wh.Names.list_seasons_for_tournament(tournament)
            elif country and not all([league, season]):
                self.league = wh.Names.list_leagues(country)
        ctx = super().get_context()
        return ctx | {'matches': self.matches}

    def get_leagues(self):
        return wh.Names.list_leagues(self.country)

    def get_seasons(self):
        return wh.Names.list_seasons_for_tournament((self.league, self.country))


class OrderCreation(TemplateView):
    template_name = "kasbeer/new-order-view.html"
    template_engine = 'jinja2'
    title = "Order Creation"
    form = FilteringForm()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["countries"] = wh.Names.list_countries()
        lbc = dict()
        for c in context['countries']:
            lbc.update({c: wh.Names.list_leagues(c)})
        context['leagues_by_countries'] = str(lbc)
        return context

    def get(self, request, *args, **kwargs):
        print('debug')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.form = FilteringForm(request.POST)
        return super().get(request, *args, **kwargs)


def leagues(request, country, **kwargs):
    ls = wh.Names.list_leagues(country.lower())
    return JsonResponse(ls, safe=False)