import re
from pyquery import PyQuery as pq
from tools.functions import get_url_query_str, url_with_query_str, try_safety, timeit, url_add_params
import urllib.parse
import base64
import requests


class Crawler:

    def page(self, url):
        r = requests.post(url)
        doc = str(r.content, 'big5', errors='ignore')
        dom = pq(doc)
        for el in dom('[id="keyad-pro-right3"]').items():
            title = el('div.pic2t > a').text().strip().replace('\n', ' ')
            href = el('a').attr.href
            print(title, href)

    def search(self, keyword):
        encode_key = urllib.parse.quote(keyword)
        store_k_word = base64.b64encode(encode_key.encode()).decode()
        base_url = 'https://www.pcstore.com.tw/adm/psearch.htm'
        url = url_add_params(base_url, store_k_word=store_k_word, slt_k_option=1)
        self.page(url)


if __name__ == '__main__':
    c = Crawler()
    keyword = input('請輸入關鍵字')
    print("關鍵字:", keyword)
    c.search(keyword)
