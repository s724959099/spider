from asyspider.crawler import Crawler
from tools import log
import logging
import re
import os
import json
from pyquery import PyQuery as pq
import random

logger = logging.getLogger(__name__)


class ProxyCrawler(Crawler):
    first_ip = ''
    headers = """
    accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
    accept-encoding: gzip, deflate, br
    accept-language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
    cache-control: no-cache
    pragma: no-cache
    upgrade-insecure-requests: 1
    """
    json_list = []
    max_tasks = 50
    proxy = False

    def on_start(self):
        if self.first_ip:
            url = self.google_url(self.first_ip)
            self.crawl(url, callback=self.google_page, kwargs=dict(ip=self.first_ip))

    def on_done(self):
        print(self.json_list)
        file_json = os.path.join('./downloads', 'proxy_list.json')
        with open(file_json, 'w')as f:
            json.dump(self.json_list, f)
        logger.info('finish')

    def getint(self, val, default=0):
        try:
            return int(re.sub('\D', '', val))
        except Exception as e:
            return default

    def google_page(self, r, ip):
        dom = pq(r.data)
        try:
            page_count = max([self.getint(el.text()) for el in dom('#navcnt>table a').items()])
        except Exception as e:
            page_count = 1
        self.parse_pages(r, page_count=page_count)
        for i in range(1, page_count):
            start = i * 10
            url = self.google_url(ip, start=start)
            self.crawl(url, callback=self.parse_pages, kwargs=dict(page_count=page_count))

    def parse_pages(self, r, page_count):
        dom = pq(r.data)
        [self.crawl(el.attr.href, callback=self.page_get_ips)
         for el in dom('h3 > a').items()]

    def page_get_ips(self, r):
        doc = r.data.decode(errors='ignore')
        ips = re.findall('\d+\.\d+\.\d+\.\d+\:\d+', doc)
        print("ips:", ips)
        self.json_list.extend(ips)

    def google_url(self, ip, start=0):
        url = 'https://www.google.com.tw/search?q={}+filetype:txt&start={}'.format(ip, start)
        return url


if __name__ == '__main__':
    log.initlog('freeproxy.log', debug=True, level=logging.DEBUG)
    crawler = ProxyCrawler()
    crawler.first_ip = '80.211.188.52'
    crawler.run()
