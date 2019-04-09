from spider import Spider, Proxy, DBProxy
from tinydb import TinyDB, Query
from pprint import pprint as pp
import re
from pyquery import PyQuery as pq
import logging
import os

db = TinyDB(os.path.join(os.path.dirname(__file__), './db.json'))
Proxies = db.table('Proxies')
query = Query()

logger = logging.getLogger('demo')


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 10
    sleep_time = None
    timeout = 10
    retries = 1
    check_crawled_urls = True
    update_cookies = True
    min_content_length = 1
    proxies_set = set()
    ProxyClass = Proxy

    def on_start(self):
        check_callbacks = lambda x: callable(getattr(self, x)) and x.startswith('crawl_')
        callbacks = [attr for attr in dir(self) if check_callbacks(attr)]
        for callback in callbacks:
            method = getattr(self, callback)
            self.add_task(method)

    def on_end(self):
        pp(self.proxies_set)
        pp(len(self.proxies_set))
        for proxy in self.proxies_set:
            ip, port = proxy.split(':')
            Proxies.insert(dict(ip=ip, port=port))
        return

    async def crawl_free_proxy_cz(self):
        """
        寫到一半 突然沒有辦法連了
        :return:
        """
        return

        async def parse(index):
            url = 'http://free-proxy.cz/zh/proxylist/main/{}'.format(index)
            r = await self.async_crawl(url)
            doc = r.content.decode()
            dom = pq(doc)
            for el in dom('#proxy_list > tbody > tr').items():
                print()

        for i in range(1, 101):
            self.add_task(parse, i)

    async def crawl_free_proxy(self):
        url = 'https://free-proxy-list.net/'
        r = await self.async_crawl(url)
        doc = r.content.decode()
        dom = pq(doc)
        for el in dom('#proxylisttable > tbody > tr').items():
            p = "{}:{}".format(el('td').eq(0).text(), el('td').eq(1).text())
            self.proxies_set.add(p)

    async def crawl_kuaidaili(self):
        page_count = 50
        for page in range(1, page_count + 1):
            url = 'https://www.kuaidaili.com/free/inha/{}/'.format(page)
            r = await self.async_crawl(url)
            doc = r.content.decode()
            ip_adress = re.compile(
                '<td data-title="IP">(.*)</td>\s*<td data-title="PORT">(\w+)</td>'
            )
            re_ip_adress = ip_adress.findall(str(doc))
            for adress, port in re_ip_adress:
                result = adress + ':' + port
                self.proxies_set.add(result.replace(' ', ''))

    async def crawl_data5u(self):
        for i in ['gngn', 'gnpt', 'gwgn', 'gwpt']:
            url = 'http://www.data5u.com/free/{}/index.shtml'.format(i)
            r = await self.async_crawl(url)
            doc = r.content.decode()
            ip_adress = re.compile(
                ' <ul class="l2">\s*<span><li>(.*?)</li></span>\s*<span style="width: 100px;"><li class=".*">(.*?)</li></span>'
            )
            # \s * 匹配空格，起到换行作用
            re_ip_adress = ip_adress.findall(str(doc))
            for adress, port in re_ip_adress:
                result = adress + ':' + port
                self.proxies_set.add(result.replace(' ', ''))

    async def crawl_premproxy(self):
        for i in ['China-01', 'China-02', 'China-03', 'China-04', 'Taiwan-01']:
            url = 'https://premproxy.com/proxy-by-country/{}.htm'.format(
                i)
            r = await self.async_crawl(url)
            doc = r.content.decode()
            dom = pq(doc)
            var_dict = {el.split('=')[0]: el.split('=')[1] for el in dom('head>script').text().split(';') if el}
            if doc:
                ip_adress = re.compile('<td data-label="IP:port ">(.*?)</td>')
                re_ip_adress = ip_adress.findall(doc)
                for adress_port in re_ip_adress:
                    ip_str = adress_port.replace(' ', '')
                    if re.match('\d+?\.\d+?.\d+?.\d+?:\d+?', ip_str):
                        res = ip_str
                    else:
                        ip = re.match('(.+?)<', ip_str).group().replace('<', '')
                        port_str = re.findall(':"(.+)\)', ip_str)[0].replace('+', '')
                        for key, val in var_dict.items():
                            port_str = port_str.replace(key, val)
                        res = "{}:{}".format(ip, port_str)
                    self.proxies_set.add(res)

    async def crawl_xroxy(self):
        for i in ['CN', 'TW']:
            url = 'http://www.xroxy.com/proxylist.php?country={}'.format(
                i)
            r = await self.async_crawl(url)
            doc = r.content.decode()
            dom = pq(doc)
            for el in dom('#DataTables_Table_0 tbody tr').items():
                ip = el('td:eq(0)').text()
                port = el('td:eq(1)').text()
                self.proxies_set.add('{}:{}'.format(ip, port))


if __name__ == '__main__':
    from tools import log

    log.initlog('DEMO', level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
