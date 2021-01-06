from asyspider.spider import Spider, Proxy, DBProxy
import re
from pyquery import PyQuery as pq
import logging
from loguru import logger
from pprint import pprint as pp
import argparse
import time
from tools.functions import get_url_query_str, url_with_query_str, try_safety, timeit, url_add_params
from urllib.parse import urljoin
import os

HOST = 'https://www.cartoonmad.com/'


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 10
    sleep_time = None
    timeout = 30
    retries = 10
    check_crawled_urls = True
    update_cookies = True
    min_content_length = 1
    proxies_set = set()
    ProxyClass = Proxy
    start_urls = [
        'https://www.cartoonmad.com/comic/7404.html'
    ]

    async def on_start(self):
        for url in self.start_urls:
            self.add_task(self.index_page, url)

    async def index_page(self, url):
        r = await self.async_crawl(url)
        doc = str(r.content, encoding='utf-8', errors='ignore')
        dom = pq(doc)
        urls = [urljoin(HOST, el.attr.href) for el in dom('td a').items()]
        urls = [url for url in urls if '/comic/' in url]
        urls = [url for url in urls if re.findall('\d{6,}', url)]
        urls = list(set(urls))
        for url in urls:
            self.add_task(self.first_pages, url)

    async def save_img(self, url, fname):
        pth = os.path.join('./data/', fname)
        if os.path.exists(pth):
            return
        r = await self.async_crawl(url)
        with open(pth, 'wb') as f:
            for chunk in r:
                f.write(chunk)

    def create_dir(self, dirname):
        pth = os.path.join('./data/', dirname)
        if not os.path.exists(pth):
            os.mkdir(pth)

    async def first_pages(self, url):
        try:
            await self.find_page(url)
        except Exception as e:
            logger.error('error: %s', url)

    async def find_page(self, url):
        r = await self.async_crawl(url)
        if not r:
            return
        doc = str(r.content, encoding='big5', errors='ignore')
        dom = pq(doc)
        dom('li > a').text()
        dirname = dom('title').text().split('-')[0].strip()
        eps = re.findall('\d+', dom('title').text().split('-')[1])[0]
        eps = int(eps)
        self.create_dir(dirname)
        page = int(dom('a.onpage').text())
        fname = '{}/{:0>3d}_{:0>2d}.jpg'.format(dirname, eps, page)
        imgs = [urljoin(url, el.attr.src) for el in dom('img').items()]
        target_img = [img for img in imgs if 'comicpic' in img][0]

        await self.save_img(target_img, fname)

        next_url = urljoin(url, dom('#sidebar-follow a').eq(-1).attr.href)
        if 'thend.asp' in next_url:
            next_url = None
        if next_url:
            await self.find_page(next_url)


if __name__ == '__main__':
    c = Crawler()
    c.run()
