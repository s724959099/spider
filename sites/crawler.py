from asyspider.spider import Spider, Proxy, DBProxy
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
import argparse
import time
from tools.functions import get_url_query_str, url_with_query_str, try_safety, timeit, url_add_params

logger = logging.getLogger('demo')


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 1
    sleep_time = None
    timeout = 30
    retries = 10
    check_crawled_urls = True
    update_cookies = True
    min_content_length = 1
    proxies_set = set()
    ProxyClass = DBProxy

    async def on_start(self):
        pass


if __name__ == '__main__':
    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
