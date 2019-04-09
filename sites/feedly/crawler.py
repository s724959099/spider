#!/Users/Admin/anaconda3/envs/py36-anaconda/bin/python
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from asyspider.spider import Spider, Proxy, DBProxy, headers_raw_to_dict
import re
from pyquery import PyQuery as pq
import logging
from tools import log
from pprint import pprint as pp
import argparse
import time
from tools.functions import (
    get_url_query_str,
    url_with_query_str,
    try_safety,
    timeit,
    url_add_params,
)
import json
from tinydb import TinyDB, Query
import os

try:
    from config import headers
except ImportError as e:
    headers = ''

db = TinyDB(os.path.join(os.path.dirname(__file__), "./db.json"))
Feedly = db.table("Feedly")
query = Query()

logger = logging.getLogger("demo")


class Crawler(Spider):
    status_code = (200, 301, 302)
    platform = "desktop"
    max_tasks = 10
    sleep_time = None
    timeout = 30
    retries = 10
    check_crawled_urls = True
    update_cookies = True
    min_content_length = 1
    proxies_set = set()
    ProxyClass = Proxy
    items = []
    headers = """
    accept: */*
    accept-encoding: gzip, deflate, br
    accept-language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
    authorization: OAuth Axv4S9AXGkwMdS1fxJ0NCUGIR_pqYMeMTPtfn0FdwenCeCt9E05vM-DGBwrN9V6jI_5mhbJkNfNjyGMgRggMA3k_gBXof0ORshPxkFal8ViadKu_Qt2kuMmdiLEoW69dSVviwFOA703yFBxBvgo0SaZGvAA9Jm1ax961mBA3A_RH40dxmaA5BiQTfPo-wzx4mi2REsH8ZiyLOp1kmBH4a2f-nBBZttQiZMaAUXuY0qr89Q:feedly
    cache-control: no-cache
    content-type: application/json
    cookie: __cfduid=d428b66bb1174a1c22bf0d8ae7a5f70e71554098296; _ga=GA1.2.49773514.1554098300; _gid=GA1.2.1222243740.1554098300; _gat_onboarding=1; _gat_unified=1; __stripe_mid=51ec7b61-a382-452c-a7a2-2a403cf00622; __stripe_sid=90132169-78e4-4444-a1b0-b71cc0004d55; SL_GWPT_Show_Hide_tmp=1; SL_wptGlobTipTmp=1; BL_D_PROV=; BL_T_PROV=; _gat_basic=1; JSESSIONID=669D1C7CDC4F1FE7738DC9509C429DBC; feedly.session={"plan":"standard","provider":"Facebook","feedlyId":"92c5a507-51e0-450f-bd03-0d47b6689410","feedlyToken":"Axv4S9AXGkwMdS1fxJ0NCUGIR_pqYMeMTPtfn0FdwenCeCt9E05vM-DGBwrN9V6jI_5mhbJkNfNjyGMgRggMA3k_gBXof0ORshPxkFal8ViadKu_Qt2kuMmdiLEoW69dSVviwFOA703yFBxBvgo0SaZGvAA9Jm1ax961mBA3A_RH40dxmaA5BiQTfPo-wzx4mi2REsH8ZiyLOp1kmBH4a2f-nBBZttQiZMaAUXuY0qr89Q:feedly","feedlyRefreshToken":"A_bbqpQWc4v6fGIUmYSk2lKwpYGSNLtB3LYr9hwGzLZWa9FfwBBMkL2soGvUx1oHjNu6mUOGpc6i5uG2gDRe_LZekurt16vzfMgsHtW0yWG9IRC4k31aRA9YKerdCcCx0g9VtcupO41GwNB04JAp80U96Ymb3l2gK6yqRJ_cxgawAGicaWBdcEKK8dSq20c4yyJ4J5MgFkBfpl5D6DG7q0Ihksw_Rr6xdE8dS325Ne73VNY:feedly","feedlyExpirationTime":1554703097408,"created":1554098307408}; feedly.leftnav.pinned=yes
    pragma: no-cache
    referer: https://feedly.com/i/my
    user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36
    """
    datas = []

    async def on_start(self):
        streams = await self.get_all_streams()
        logger.info("streams count: %s", len(streams))
        for stream in streams:
            self.add_task(self.parse_stream, stream)

    def on_end(self):
        print(Feedly.insert_multiple(self.datas))
        print('found: ', len(self.datas))

    async def get_all_streams(self):
        url = "https://feedly.com/v3/subscriptions?ct=feedly.desktop&cv=undefined&ck=1552029860872&withStats=true"
        r = await self.async_crawl(url)
        doc = r.content.decode()
        streams = json.loads(doc)
        return streams

    async def parse_stream(self, stream):
        continuation = None
        page_index = 0
        while page_index < 100:
            page_index += 1
            url = self.get_api(stream["id"], continuation)
            r = await self.async_crawl(url)
            if not r:
                break
            # logger.info('page_count: %s %s', page_index, stream['title'])
            doc = r.content.decode()
            js = json.loads(doc)
            self.insert_items(js["items"], category=stream["title"])
            if not js.get("continuation") or not js["items"]:
                break
            continuation = js["continuation"]

    def insert_items(self, items, category):
        for item in items:
            content = item["summary"]["content"] if item.get("summary") else ""
            if re.findall("</.+?>", content):
                dom = pq(content)
                content = dom.text().strip()
            dct = dict(
                title=item["title"],
                content=content,
                url=item["alternate"][0]["href"],
                category=category,
            )
            self.datas.append(dct)
            print(item["title"], dct["url"])

    def get_api(self, stream_id, continuation=None):
        api = "https://feedly.com/v3/streams/contents"
        ts = str(time.time()).replace(".", "")[:13]
        params = headers_raw_to_dict(
            """
            streamId: {}
            count: 40
            unreadOnly: true
            ranked: newest
            similar: true
            ck: {}
            ct: feedly.desktop
            cv: 31.0.269
            continuation: {}
            """.format(
                stream_id, ts, continuation
            )
        )
        if not params["continuation"]:
            del params["continuation"]
        return url_add_params(api, **params)


if __name__ == "__main__":
    log.initlog("DEMO", level=logging.DEBUG, debug=True)
    c = Crawler()
    c.run()
