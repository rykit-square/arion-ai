#!/usr/bin/python
# coding: utf-8

import re
import requests
from bs4 import BeautifulSoup
from enum import Enum, auto
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from pprint import pprint


class Scraper(object):

    def __init__(self):
        pass

    def retrieve_html(self, url):
        req = requests.get(url)
        soup = BeautifulSoup(req.content, "html.parser")
        return soup


class ResultScaraper(Scraper):

    score_labels = (
        "arrival_order",
        "frame_num",
        "horse_num",
        "horse_name",
        "horse_info",
        "arrival_diff",
        "time",
        "last3f_time",
        "passing_order",
        "jockey_name",
        "jockey_weight",
        "odds",
        "popularity",
        "trainer_name",
    )

    horse_info_labels = (
        "horse_sex",
        "horse_age",
        "horse_weight",
        "horse_weight_diff",
        "horse_b",
    )

    def __init__(self):
        super(ResultScaraper, self).__init__()

    def extract_race_info(self, soup):
        pass

    def extract_scores(self, soup):
        scores = []
        table = soup.select("table#raceScore")[0]
        for tr_tag in table.select("tbody > tr"):
            score = []
            for td_tag in tr_tag.select("td"):
                # <a>タグ
                a_tags = td_tag.select("a")
                if a_tags:
                    score.append(a_tags[0].get_text().strip("()\t\n\x0b\x0c\r "))
                    a_tags[0].extract()
                # <span>タグ
                span_tags = td_tag.select("span")
                if span_tags:
                    score.append(span_tags[0].get_text().strip("()\t\n\x0b\x0c\r "))
                    span_tags[0].extract()
                # 上記以外
                td_text = td_tag.get_text().strip()
                if td_text:
                    score.append(td_text)
            # データを保存
            score = OrderedDict(zip(self.score_labels, score))
            scores.append(score)
        return scores

    def parse_scores(self, scores):
        for score in scores:
            score["time"] = self._parse_time(score["time"])
            # score["horse_info"] = self._parse_horse_info(score["horse_info"])
            self._conv_digit(score)
        return scores

    def _parse_horse_info(self, horse_info):
        s = re.search("(牡|牝|せん)(\d+)/(\d+)\(([\+\-]?\d+)\)/(B?)", horse_info)
        if s:
            return OrderedDict(zip(self.horse_info_labels, s.groups()))
        else:
            raise

    def _parse_time(self, time):
        t = time.split(".")
        if len(t) == 2:
            sec = float(time)
        elif len(t) == 3:
            sec = "{}.{}".format(float(t[0]) * 60.0 + float(t[1]), float(t[2]))
        return sec

    def _conv_digit(self, score):
        for k, v in score.items():
            if v == '':
                score[k] = None
            elif v.isdigit():
                score[k] = int(v)
            else:
                try:
                    score[k] = float(v)
                except ValueError:
                    pass


def test_scraper(url):
    scraper = ResultScaraper()
    soup = scraper.retrieve_html(url)
    scores = scraper.extract_scores(soup)
    scores = scraper.parse_scores(scores)
    return scores


if __name__ == "__main__":
    url = "https://keiba.yahoo.co.jp/race/result/1906030211/"
    scores = test_scraper(url)
    pprint(scores)


