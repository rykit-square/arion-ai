#!/usr/bin/python
#-*-coding: utf-8-*-

import os
import sys
import re
import lxml
import urllib
from bs4 import BeautifulSoup
from pprint import pprint


TAG = re.compile((r'<[^>]*?>'))
SPACE = re.compile((r'[\s]+'))
NEWLINE = re.compile(r'[\n]+')
SYMBOL = re.compile(r'[\(\)\[\]/\|]')
ALLOWED_URL = re.compile(r'/race/result/|/directory/horse/')

RACE_INFO = ('date',
             '',
             )

RACE_RSLT = ('arrival_order',
             'frame_num',
             'horse_num',
             'horse_info',
             'time',
             'passing_last3f',
             'jocky',
             'odds',
             'trainer',
             )


class YahooKeibaCrawler(object):

    def __init__(self, base_url):
        self.base_url = base_url

    def fetch_url(self, url):
        try:
            response = urllib.request.urlopen(url)
            soup = BeautifulSoup(response.read(), 'lxml')
        except urllib.error.HTTPError:
            print('could not find url:', url)
            raise

        # extract urls and results of race and horse, separately
        if '/race/result/' in url:
            urls = self._extract_urls(soup)
            race_info = self._extract_race_info(soup)
            race_rslt = self._extract_race_rslt(soup)
        elif '/directory/horse/' in url:
            urls = self._extract_urls(soup)
            race_info = None
            race_rslt = None
        else:
            urls = None
            race_info = None
            race_rslt = None

        return urls, race_info, race_rslt

    def _extract_urls(self, soup):
        urls = soup.find_all('a', href=ALLOWED_URL)
        return [self.base_url + u['href'] for u in urls]

    def _extract_race_info(self, soup):
        race_info = soup.find('table', {'id': 'raceHead', 'class': 'mgnBM'})
        race_info = race_info.find('div', {'id': 'raceTit'})
        race_img = race_info.find_all('img')
        race_info = race_info.text.split('|')[: 5]
        race_info[3] += race_img[0]['alt']
        race_info[4] += race_img[1]['alt']
        return race_info

    def _extract_race_rslt(self, soup):
        denmas = soup.find('table', {'id': 'raceScore', 'class': 'dataLs mgnBS'})
        denmas = denmas.find('tbody')
        denmas = denmas.find_all('tr')
        race_rslt = []
        for denma in denmas:
            cols = denma.find_all('td')
            cols = [re.sub(TAG, ',', str(c)) for c in cols]
            race_rslt.append(cols)
        return race_rslt

    def _check_columns(self, cols):
        columns = []
        for col in cols:
            elems = col.split(',')
            elems = [e for e in elems if e != '']
            columns.extend(elems)
        return columns


if __name__ == '__main__':
    base_url = 'https://keiba.yahoo.co.jp'
    url = 'https://keiba.yahoo.co.jp/race/result/1608040711/'
    crawler = YahooKeibaCrawler(base_url)
    urls, race_info, race_rslt = crawler.fetch_url(url)

    pprint(urls)
    pprint(race_info)
    pprint(race_rslt)