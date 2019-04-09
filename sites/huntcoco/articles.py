#!/Users/Admin/anaconda3/envs/py36-anaconda/bin/python
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from asyspider.spider import Spider, Proxy, DBProxy, headers_raw_to_dict
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
from pprint import pformat
import argparse
import time
from urllib.parse import urljoin
from tinydb import TinyDB, Query
import os

db = TinyDB(os.path.join(os.path.dirname(__file__), './db.json'))
articles = db.table('articles')
query = Query()

logger = logging.getLogger('demo')
HOST = 'http://www.huntcoco.com/index.php'


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

    async def on_start(self):
        await self.login()
        url = 'http://www.huntcoco.com/index.php'
        r = await self.async_crawl(url)
        doc = r.content.decode()
        dom = pq(doc)
        self.parse_all_pages(dom)

    def parse_all_pages(self, dom):
        urls = [urljoin(HOST, el.attr.href) for el in dom('a').items() if
                el.attr.href and HOST in urljoin(HOST, el.attr.href)]
        for url in urls:
            self.add_task(self.insert_to_db, url)

    async def insert_to_db(self, url):
        await self.login()
        r = await self.async_crawl(url)
        if not r:
            return
        doc = r.content.decode()
        dom = pq(doc)
        self.parse_all_pages(dom)

        title = dom('td > span').text()
        content = dom('body').text()
        ret = dict(
            url=url,
            title=title,
            content=content
        )
        # articles.insert(ret)

    async def login(self):
        url = 'http://www.huntcoco.com/member/account_login1.php'
        r = await self.async_crawl(url, method='POST', headers="""
        Accept: */*
        Accept-Encoding: gzip, deflate
        Accept-Language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
        Cache-Control: no-cache
        Connection: keep-alive
        Content-Length: 46
        Content-Type: application/x-www-form-urlencoded; charset=UTF-8
        Host: www.huntcoco.com
        Origin: http://www.huntcoco.com
        Pragma: no-cache
        Referer: http://www.huntcoco.com/index.php?goto=41
        User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36
        X-Requested-With: XMLHttpRequest
        """, data=headers_raw_to_dict("""
        a: nomoneynolove20130610@gmail.com
        b: ji394su3
        """))


if __name__ == '__main__':
    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
