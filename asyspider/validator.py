from asyspider import *
from pyquery import PyQuery as pq
import re


class VProxyHandler(ProxyHandler):
    i = 0

    def get_proxy(self):
        if len(self.proxy_list.get('data')):
            proxy = self.proxy_list.get('data')[self.i % len(self.proxy_list)]
        else:
            proxy = None
        self.i += 1
        return proxy


class Validator(Crawler):
    check_crawled_urls = False
    proxy = True
    retries = 1
    fail_try_num = 0
    max_tasks = 20
    timeout = 5
    proxy_handler = VProxyHandler()

    def on_start(self):
        url = 'https://allinfa.com/ipcheck/'
        for proxy in self.proxy_handler.proxy_list.get('data'):
            self.crawl(url, callback=self.index_page, proxy=proxy)

    def index_page(self, r):
        dom = pq(r.result)
        data = dom('.entry > p:eq(1)').text()
        data = self.testing(data)
        # todo 判斷Anonymity

    def testing(self, data):
        lines = data.split('\n')
        ret = dict()
        for line in lines:
            line = line.replace('您現在上網的真實', '')
            if not line:
                continue
            try:
                key, val = line.split('：')
            except Exception as e:
                continue

            ret[key.strip().replace(' ', '_')] = val.strip()
        return ret

    def on_done(self):
        self.proxy_handler.save_proxies()
        logger.info('proxis len: %s', len(self.proxy_handler.proxy_list.get('data')))


if __name__ == '__main__':
    import logging
    from tools.log import initlog, logger

    initlog('validate', level=logging.DEBUG, debug=True)
    Validator().run()
