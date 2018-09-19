import os
import json
import random
from .utils import *

dir_path = os.path.dirname(os.path.realpath(__file__))


def read_proxy():
    proxy_path = 'proxy.json'
    try:
        proxy_data = read_json(proxy_path)
    except Exception as e:
        proxy_data = dict(data=[], keys=[])
    return proxy_data


def save_to_proxy(data):
    proxy_path = 'proxy.json'
    proxy_data = read_proxy()

    for el in data:
        key = "{}:{}".format(el.get('ip'), el.get('port'))
        if key not in proxy_data.get('keys', []):
            el['key'] = key
            proxy_data['data'].insert(0, el)
            proxy_data['keys'].append(key)

    save_json(proxy_path, proxy_data)


class ProxyHandler:
    proxy_list = read_proxy()

    def dead_proxy(self, proxy):
        # todo
        if proxy in self.proxy_list.get('data'):
            self.proxy_list.get('keys').remove(proxy.get('key'))
            self.proxy_list.get('data').remove(proxy)

    def get_proxy(self):
        if len(self.proxy_list.get('data')):
            proxy = random.choice(self.proxy_list.get('data'))
        else:
            proxy = None
        return proxy

    def save_proxies(self):
        proxy_path = 'proxy.json'
        save_json(proxy_path, self.proxy_list)


if __name__ == '__main__':
    p = ProxyHandler()
    print('finish')
