from asyspider.crawler import Crawler
from tools import log
import logging
import re
# todo checing needed
import aiohttp
import os
import json
from pyquery import PyQuery as pq
import random

logger = logging.getLogger(__name__)


class TestCrawler(Crawler):
    max_tasks = 40
    check_crawled_urls = False
    timeout = 99999999
    headers = """
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
    Accept-Encoding: gzip, deflate, br
    Accept-Language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
    Cache-Control: no-cache
    Connection: keep-alive
    Host: www.youjizz.com
    Pragma: no-cache
    Referer: https://www.youjizz.com/
    Upgrade-Insecure-Requests: 1
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36
    """
    urls = """
    https://www.youjizz.com/videos/lesbian-colleges-and-teens-at-home-jenna-sativa%2c-sara-luvv%2c-val-dodds%2c-madi-meadows%2c-leah-gotti-32859291.html
    https://www.youjizz.com/videos/dg---leah-gotti-deep-creampie-35336821.html
    https://www.youjizz.com/videos/full-hd-video---leah-gotti-stretched-to-the-max-by-huge-cock%21-45023411.html
    https://www.youjizz.com/videos/leah-gotti-oil-anal-35094171.html
    https://www.youjizz.com/videos/tiny4k-leah-gotti-soaking-up-the-sun-34815791.html
    https://www.youjizz.com/videos/leah-gotti-38748601.html
    https://www.youjizz.com/videos/leah-gotti-first-time-38284111.html
    https://www.youjizz.com/videos/leah-with-boss-42533701.html
    https://www.youjizz.com/videos/leah-gotti-born-for-porn-41306961.html
    """

    def on_start(self):
        for url in self.urls.split():
            self.crawl(url, callback=self.get_index)

    def get_index(self, r):
        def random_ip():
            a = random.randint(1, 255)
            b = random.randint(1, 255)
            c = random.randint(1, 255)
            d = random.randint(1, 255)
            return (str(a) + '.' + str(b) + '.' + str(c) + '.' + str(d))

        headers = """
        X-Forwarded-For: {}
        """.format(random_ip())
        doc = r.data.decode()
        dom = pq(doc)
        file_name = dom('title').text() + '.mp4'
        file_name = os.path.join('./downloads', file_name)
        json_data = json.loads(re.findall(r'var encodings = (.*?);', doc)[0])
        ret = None
        for data in json_data:
            if ret is None:
                ret = data
                continue
            if int(data.get('quality')) > int(ret.get('quality')):
                ret = data
        if ret is None:
            return ret
        url = 'https:' + ret.get('filename')
        print(url)
        self.download(url, file_name, headers=headers)


if __name__ == '__main__':
    log.initlog('d_demo', level=logging.DEBUG, debug=True)
    c = TestCrawler()
    c.run()
