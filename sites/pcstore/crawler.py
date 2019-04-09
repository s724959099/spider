from asyspider.spider import Spider, Proxy, DBProxy
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
import argparse
import time
from tools.functions import get_url_query_str, url_with_query_str, try_safety, timeit, url_add_params
import urllib.parse
import base64

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
    ProxyClass = Proxy

    async def on_start(self):
        encode_key = urllib.parse.quote(self.keyword)
        store_k_word = base64.b64encode(encode_key.encode()).decode()
        base_url = 'https://www.pcstore.com.tw/adm/psearch.htm'
        url = url_add_params(base_url, store_k_word=store_k_word, slt_k_option=1)
        await self.page(url)

    async def page(self, url):
        r = await self.async_crawl(url, method='POST')
        doc = str(r.content, 'big5', errors='ignore')
        dom = pq(doc)
        for el in dom('[id="keyad-pro-right3"]').items():
            title = el('div.pic2t > a').text().strip().replace('\n', ' ')
            href = el('a').attr.href
            print(title, href)

    def search(self, keyword):
        self.keyword = keyword
        self.run()


if __name__ == '__main__':
    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    keyword = input('請輸入關鍵字')
    print("關鍵字:", keyword)
    c.search(keyword)
