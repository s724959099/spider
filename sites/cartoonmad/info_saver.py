from asyspider.spider import Spider, Proxy, DBProxy
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
import argparse
import time
from tools.functions import get_url_query_str, url_with_query_str, try_safety, timeit, url_add_params
from urllib.parse import urljoin
import os
import json

logger = logging.getLogger('demo')
HOST = 'https://www.cartoonmad.com/'


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 15
    sleep_time = None
    timeout = 30
    retries = 10
    check_crawled_urls = True
    update_cookies = True
    min_content_length = 1
    proxies_set = set()
    ProxyClass = Proxy
    start_urls = [
        'https://www.cartoonmad.com/'
    ]
    datas = []

    async def on_start(self):
        for url in self.start_urls:
            self.add_task(self.index_page, url)

    async def index_page(self, url):
        r = await self.async_crawl(url)
        doc = str(r.content, encoding='big5', errors='ignore')
        dom = pq(doc)
        urls = [urljoin(HOST, el.attr.href) for el in dom('[bgcolor="#C1C1C1"] a').items()]
        urls = list(set(urls))
        for url in urls:
            self.add_task(self.pages, url)

    # def on_start(self):
    #     url = 'https://www.cartoonmad.com/comic/5409.html'
    #     self.add_task(self.page_info, url)

    def on_end(self):
        with open('./data.json', 'w') as f:
            f.write(json.dumps(self.datas))

    async def pages(self, url):
        r = await self.async_crawl(url)
        if not r:
            return
        doc = str(r.content, encoding='big5', errors='ignore')
        dom = pq(doc)
        urls = [urljoin(url, el.attr.href) for el in dom('a.a1').items()]
        for url in urls:
            self.add_task(self.page_info, url)
        next_url = urljoin(HOST, dom('td[width="88"] > a.pages').eq(-1).attr.href)
        self.add_task(self.pages, next_url)

    async def page_info(self, url):
        r = await self.async_crawl(url)
        doc = str(r.content, encoding='big5', errors='ignore')
        dom = pq(doc)
        title = dom('title').text().split('-')[0].strip()
        el = [el for el in dom('td td td td').items() if '推薦指數' in el.text()][0]
        recomand = int(re.sub('[^\d]', '', el.text()))
        el = [el for el in dom('td td td td').items() if '收錄' in el.text()][0]
        txt = el.text().split('~')[-1]
        eps = int(re.sub('[^\d]', '', txt))
        desc = dom('#info > [cellspacing="8"] td').text()
        dct = dict(
            title=title,
            url=url,
            recomand=recomand,
            desc=desc,
            eps=eps
        )
        self.datas.append(dct)


if __name__ == '__main__':
    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
