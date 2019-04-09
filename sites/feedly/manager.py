#!/Users/Admin/anaconda3/envs/py36-anaconda/bin/python
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import re
import logging
from tools import log
from pprint import pprint as pp
import argparse
import time
from tools.functions import get_url_query_str, url_with_query_str, try_safety, timeit, url_add_params
import json
from tinydb import TinyDB, Query
import os
import collections

db = TinyDB(os.path.join(os.path.dirname(__file__), './db.json'))
Feedly = db.table('Feedly')
query = Query()


def get_categories_info():
    dct = collections.defaultdict(int)
    for el in Feedly.all():
        try:
            dct[el['category']] += 1
        except Exception as e:
            Feedly.remove(doc_ids=[el.doc_id])

    return dct


def get_articles():
    return Feedly.all()


def get_articles_by_categories(category):
    return Feedly.search(query.category == category)


def article_with_keywords(articles):
    pass


def remove_articles_by_categories(category):
    return Feedly.remove(query.category == category)


if __name__ == '__main__':
    keywords = []
    with open(os.path.join(os.path.dirname(__file__), 'keyword.txt'), 'r', encoding="utf-8") as f:
        keywords = f.read().split('\n')
    pattern = "|".join(keywords)
    for el in get_articles():
        if any([
            re.findall(pattern, el['title'].lower()),
            re.findall(pattern, el['content'].lower())
        ]):
            continue
        print(el['title'], el['content'][:20])
    print()
