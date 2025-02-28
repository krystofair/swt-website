"""
    Models for analysis results to build specific required by view contexts
    after loading data.
"""
import pandas as pd
try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

from io import StringIO
import importlib
import copy
import logging
from functools import cached_property

from . import tasks, charts

logger = logging.getLogger(__name__)


class ResultService:
    REGISTRY = {}

    @classmethod
    def sign_for(cls, task):
        def wrapper(result_class):
            # TODO: Analysis could be more than one results class.
            cls.REGISTRY[task.__qualname__] = result_class
            return result_class

        return wrapper

    @classmethod
    def _select(cls, job):
        return cls.REGISTRY.get(job.analysis().task_func, None)

    @classmethod
    def apexcharts_build(cls, jobs):
        """Build context to use with ApexChart"""
        results = dict()
        errors = list()
        for job in jobs:
            if job.error or job.result is None:
              errors.append(ErrorResult(job, msg="Analiza jeszcze nie obliczona"))
              continue
            ResultClass = cls._select(job)
            # TODO: ResultClass never should be None in real situation,
            #       because this won't processed code review.
            if ResultClass is not None:
                result_data = jsonlib.loads(StringIO(job.result).read())
                df = pd.DataFrame.from_dict(result_data)
                # logger.debug(df)
            else:
                logger.warning(
                    "Not found ResultClass for analysis: {}".format(job.analysis_name)
                )
                continue  # skip.
            rc = ResultClass(df)
            try:
                results.update(rc.apex)
            except (AttributeError, NotImplementedError):
                pass
            except ValueError as e:
                logger.error(e)
                errors.append(ErrorResult(job, msg=e))
            except Exception as e:
                logger.exception(e)
                errors.append(ErrorResult(job, msg="Wystapily inne bledy, powiadom admina."))
        return results, errors


sign_for = ResultService.sign_for


class ErrorResult:
    def __init__(self, job, msg):
        self.message = job.error or msg
        self.analysis = job.analysis_name


class Result:
    """
    Option JSON which describe how chart will look like.
    Read "ApexCharts" docs for constructing option.
    For basic view template `m2/base.html` is used.
    """

    def __init__(self, dataframe):
        self.dataframe = dataframe

    @cached_property
    def apex(self):
        """Should be override if a class is able to generate ApexChart context."""
        raise NotImplementedError


@sign_for(tasks.analyse_corners_line_auto)
class CornerLineAnalysisResult1(Result):
    sample_option = {
        "chart": {"type": "bar"},
        "series": [],
        # series object is:
        # {
        #   "name": 'sales',
        #   "data": [30, 40, 35, 50, 49, 60, 70, 91, 120]
        # }
        "xaxis": {"categories": [1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999]},
    }

    @cached_property
    def apex(self):
        option = copy.deepcopy(self.sample_option)
        df = self.dataframe
        for c in ["home", "away"]:
            option["series"].append({"name": c, "data": list(df[c])})
        option["xaxis"]["categories"] = list(df["match_id"])
        return {"straightforward stats": option}


@sign_for(tasks.corners_box_describe_totals)
class CornerDescribe(Result):
    @cached_property
    def apex(self, **kwargs):
        plot = charts.AreaChartDescribe()
        plot.add_line("total", *list(self.dataframe.loc[:, "total"]))
        return {"describe corners": plot.apex()}


@sign_for(tasks.analyse_corners_2)
class CornersLinesResult2(Result):
    @cached_property
    def apex(self, **kwargs):
        return self.stack_bar_plot()

    def stack_bar_plot(self, **kwargs):
        plot = charts.StackBarPlot()
        plot.options.update(plot.custom_yaxis_title("weight"))
        plot.add_serie(
            "weight_over",
            self.dataframe.columns,
            list(self.dataframe.loc["weight_over", :]),
        )
        plot.add_serie(
            "weight_under",
            self.dataframe.columns,
            list(self.dataframe.loc["weight_under", :]),
        )
        plot.add_serie(
            "diff_abs", self.dataframe.columns, list(self.dataframe.loc["diff_abs", :])
        )
        return {"stackbar plot": plot.apex()}

@sign_for(tasks.correlation_rate_on_off_to_result)
class TeamScoringOnPieChart(Result):
    @cached_property
    def apex(self, **kwargs):
        plot = charts.StackBarPlot()
        #plot = charts.PieChart()
        points_dict = self.dataframe.set_index('team_name').to_dict().get('points', {})
        newd = {k: v for k, v in points_dict.items() if v > 0}
        if len(newd) == 0:
          raise ValueError("Brak sensownych danych.")
        plot.add_serie("punkty", newd.keys(), newd.values())
        # plot.fill_whole_pie(points_dict)
        logger.debug(plot.apex())
        return {'korelacja strzaly-wynik': plot.apex()}