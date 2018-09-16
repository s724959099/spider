import os
import json
import random

dir_path = os.path.dirname(os.path.realpath(__file__))


class Proxy:
    file_name = os.path.join(dir_path, './datas', 'proxy_list.json')

    def __init__(self):
        with open(self.file_name, 'r')as f:
            self.proxy_list = json.loads(f.read())

    def dead_proxy(self, proxy):
        if proxy in self.proxy_list:
            self.proxy_list.remove(proxy)

    def get_proxy(self):
        proxy = random.choice(self.proxy_list)
        return proxy

    def store(self):
        with open(self.file_name, 'w')as f:
            json.dump(self.proxy_list, f)


if __name__ == '__main__':
    p = Proxy()
    print('finish')
