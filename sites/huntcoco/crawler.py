from asyspider.spider import Spider, Proxy, DBProxy, headers_raw_to_dict
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
from pprint import pformat
import argparse
import time

try:
    from config import account, password
except ImportError as e:
    account = ''
    password = ''

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
        await self.login()
        url = 'http://www.huntcoco.com/index.php?&goto=7701'
        r = await self.async_crawl(url, headers="""
        Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
        Accept-Encoding: gzip, deflate
        Accept-Language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
        Cache-Control: no-cache
        Connection: keep-alive
        Host: www.huntcoco.com
        Pragma: no-cache
        Referer: http://www.huntcoco.com/index.php?goto=7704
        Upgrade-Insecure-Requests: 1
        User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36
        """)
        doc = r.content.decode()
        dom = pq(doc)
        powerdown = dom('#powerdown > span').text()
        powerup = dom('#powerup > span').text()
        specialprice = dom('#specialprice > span').text()
        pressure1 = dom('[id="pressure1"] > span').text()
        pressure2 = dom('[id="pressure2"] > span').text()
        support1 = dom('[id="support1"] > span').text()
        support2 = dom('[id="support2"] > span').text()
        logger.info("\n %s", pformat(dict(
            powerdown=powerdown,
            powerup=powerup,
            specialprice=specialprice,
            pressure1=pressure1,
            pressure2=pressure2,
            support1=support1,
            support2=support2,
        )))

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
        a: {}
        b: {}
        """.format(account, password)))


if __name__ == '__main__':
    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
