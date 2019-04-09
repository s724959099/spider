from spider import Spider
from tinydb import TinyDB, Query
from pprint import pprint as pp
import re
from pyquery import PyQuery as pq
import logging
import os

db = TinyDB(os.path.join(os.path.dirname(__file__),'./db.json'))
Proxies = db.table('Proxies')
query = Query()
test_url = 'https://s.yimg.com/cv/apiv2/tw/sundar/2019/mar/15/02767911/0318_1.png'

logger = logging.getLogger('demo')


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 30
    sleep_time = None
    timeout = 5
    retries = 1
    check_crawled_urls = False
    update_cookies = True
    min_content_length = 1
    proxies = []
    headers = """
    Referer: https://tw.yahoo.com/
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36
    """

    async def on_start(self):
        for p in Proxies.all():
            self.add_task(self.validate, p)

    def on_end(self):
        logger.info('p len: %s', len(self.proxies))

    async def validate(self, p):
        proxy = "http://{}:{}".format(p['ip'], p['port'])
        proxies = dict(http=proxy, https=proxy)
        r = await self.async_crawl(test_url, proxies=proxies)
        if not r:
            Proxies.remove(doc_ids=[p.doc_id])
        else:
            self.proxies.append(p)


if __name__ == '__main__':
    from tools import log

    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
