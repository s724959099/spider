#!/Users/Admin/anaconda3/envs/py36-anaconda/bin/python
import sys
sys.path.append('/Users/Admin/Desktop/Others/程式/MyProjects/my_git/spider')
from asyspider.spider import Spider, Proxy, DBProxy
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
import argparse
import time

logger = logging.getLogger('demo')


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 10
    sleep_time = None
    timeout = 10
    retries = 1
    check_crawled_urls = False
    update_cookies = True
    min_content_length = 1
    proxies_set = set()
    ProxyClass = DBProxy

    async def on_start(self):
        try:
            while True:
                res = await self.print_point()
                if res:
                    time.sleep(self.sleep_time)
        except KeyboardInterrupt as e:
            print('end')

    async def print_point(self):
        url = 'https://www.wantgoo.com/option/futures/_%E8%A1%A8%E6%A0%BC_%E6%9C%9F%E8%B2%A8_%E4%B8%8A%E6%96%B9_%E9%96%8B%E9%AB%98%E4%BD%8E%E6%94%B6_%E5%9F%BA%E6%9C%AC%E8%B3%87%E8%A8%8A_futuresonly?StockNo=WTX%2526'
        r = await self.async_crawl(url)
        if not r:
            return False
        dom = pq(r.content.decode())

        now_pt = int(dom('span.price').text())
        oepn_pt = int(dom('.idx-data-pri > li > b.i').eq(0).text())
        high_pt = int(dom('.idx-data-pri > li > b.i').eq(1).text())
        low_pt = int(dom('.idx-data-pri > li > b.i').eq(2).text())
        if (now_pt >= self.high_limit or now_pt <= self.low_limit) and \
                self.high_limit and self.low_limit:
            logger.warning('open: %s high: %s low: %s close: %s !!!!!!!!', oepn_pt, high_pt, low_pt, now_pt)
        else:
            logger.info('open: %s high: %s low: %s close: %s', oepn_pt, high_pt, low_pt, now_pt)
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--low", help="low", type=int, default=0)
    parser.add_argument("-g", "--high", help="high", type=int, default=0)
    args = parser.parse_args()
    log.initlog('DEMO', level=logging.INFO, debug=True)
    c = Crawler()
    high_limit = 10450
    low_limit = 10430
    c.sleep_time = 30
    c.low_limit = int(low_limit)
    c.high_limit = int(high_limit)
    c.run()
