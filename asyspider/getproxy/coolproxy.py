from config import *
from asyspider import *
from pyquery import PyQuery as pq
import re
import base64
import codecs


class Spider(Crawler):
    check_crawled_urls = False
    max_tasks = 20
    timeout = 10
    retries = 1
    sleep_time = 1
    proxy = False
    result = []

    def on_start(self):
        for page in range(1, 9 + 1):
            url = 'http://www.cool-proxy.net/proxies/http_proxy_list/sort:score/direction:desc/page:{page}'.format(
                page=page)
            self.crawl(url, callback=self.index_page)

    def index_page(self, r):
        pp('get url: %s' % str(r.url))
        dom = pq(r.result)
        for _el in dom('tr').items():
            if not len(_el('td')):
                continue
            el = lambda x: _el('td:eq({})'.format(x)).text()
            el(0)
            bs_ip = re.findall('"(.+?)"', el(0))[0]
            try:
                ip = base64.b64decode(codecs.decode(bs_ip.strip(), 'rot-13')).strip().decode()
            except Exception as e:
                continue

            self.result.append(dict(
                source='coolproxy',
                country=el(3),
                ip=ip,
                port=el(1),
                anonymity=el(5)
            ))

    def on_done(self):
        pp(self.result)
        pp('result len: %s' % len(self.result))
        save_to_proxy(self.result)


if __name__ == '__main__':
    Spider().run()
