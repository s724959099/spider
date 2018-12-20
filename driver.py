from selenium import webdriver
from contextlib import contextmanager
import os
from pprint import pprint as pp
import requests
from pyquery import PyQuery as pq
import re
from functions import *


def headers_raw_to_dict(headers_raw):
    """
    Convert raw headers (single multi-line bytestring)
    to a dictionary.
    For example:
    from copyheaders import headers_raw_to_dict
    headers_raw_to_dict(b"Content-type: text/html\n\rAccept: gzip\n\n")   # doctest: +SKIP
    {'Content-type': ['text/html'], 'Accept': ['gzip']}
    Incorrect input:
    headers_raw_to_dict(b"Content-typt gzip\n\n")
    {}
    Argument is ``None`` (return ``None``):
    headers_raw_to_dict(None)
    """

    if headers_raw is None:
        return None
    headers = headers_raw.splitlines()
    headers_tuples = [header.split(':', 1) for header in headers]

    result_dict = {}
    for header_item in headers_tuples:
        if not len(header_item) == 2:
            continue

        item_key = header_item[0].strip()
        item_value = header_item[1].strip()
        result_dict[item_key] = item_value

    return result_dict


@contextmanager
def chrome_driver(
        driver_path=os.path.join('/usr/local/bin', 'chromedriver'),
):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1200x600')
    # options.add_argument('--proxy-server=%s' % proxy['http'])

    driver = webdriver.Chrome(executable_path=driver_path, chrome_options=options)
    driver.start_client()
    yield driver
    driver.close()
    driver.quit()


def chrome_dirver_get_cookies(url,
                              driver_path=os.path.join(os.environ['HOME'], 'chromedriver'),
                              ):
    cookies = ''
    with chrome_driver(driver_path=driver_path) as driver:
        driver.get(url)
        cookies = driver.get_cookies()
        cookies = '; '.join([i['name'] + '=' + i['value'] for i in cookies])
    return cookies


if __name__ == '__main__':
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException
    import time
    import re
    from selenium.webdriver.common.action_chains import ActionChains
    from pprint import pprint as pp
    import json

    url = 'https://www.lazada.co.th/shop-smart-tracking/?ajax=True&page=1'
    session = requests.session()

    with chrome_driver()as web:
        delay = 30
        web.get(url)
        web.implicitly_wait(10)
        with open('./c.js', 'r') as f:
            js = f.read()
        web.execute_script(js)
        n = web.execute_script("""
                    var t = {
                        Flag: 880846,
                        GPInterval: 50,
                        MPInterval: 4,
                        MaxFocusLog: 6,
                        MaxGPLog: 1,
                        MaxKSLog: 14,
                        MaxMCLog: 12,
                        MaxMPLog: 5,
                        MaxMTLog: 500,
                        MaxNGPLog: 1,
                        MaxTCLog: 12,
                        MinMTDwnLog: 30,
                        OnlyHost: 1,
                        SendInterval: 5,
                        SendMethod: 8,
                        api: 1,
                        font: 1,
                        hook: 1,
                        sIDs: ["_n1t|_n1z|nocaptcha|-stage-1"]
                    }

                    try {
                        var a = window.h(5,t);
                        return a
                    } catch (e) {
                        return 3333
                    }
                    """)
        n = '114#GoHEr98dTTobrsbrNsmj6YbDyHO8Nn1yfu5vm0eQoFC3+xVYYfr+tG1gb3+S7IltL16YEjSvBWNTp4j32ICOQgectzPUbzdUZR9a4QguDQs3wSOiyzphnZ3sHEaNiRmXnLxRR/URJ0zNfjMtzKdOsczA6vgDdwP7LWZqozvd3eQP1P13LHeTAe7IOLMwXPXMFZFpzm+EXMF2Re8/WWkKxIgA1Mk30KWM7pKbCLXd4BXJ6FdZAcclLtvj+PZuRssW0ipL/OP70tC2TcTame18xY0H3boaKCJ8TnXTnju8fMaT8mTs2/D9fImXTgB0Ayx8VKMLX9u8JtHtmfjf2Q7mf9fXwWwRSu20jjTWWmiDfMaoitTdoQ6tFTT6Nsm4HtO8vBt0Iw3RFHR0dgvRT9sd6T9NX0OeID6CzYQO1GKQV2PstWaWQCUl0sdoHQl0U53nWkE85K99YI+qcZMi9TKIgrqReyDZ3N6EQw/cXWQYvoLskEZY6N9APH8gA9yjIDA2uuCj08KnfUNnKICHFbUgEMlMcJ8OkXb5WZqR+Rf8sLzTvaozh5YLNttRFNdvyyw4Kfiy+Sb9kAy7+ZpXVsUieTp/IlqHZAAotjFCAjZKiGuRd8y9XS/='
        doc = web.page_source
        dom = pq(doc)
        t = dom('[name="nc_token"]').attr.value
        a = re.findall('appkey: "(.+?)",', doc)[0]
        x5secdata = dom('[name="x5secdata"]').attr.value
        x5step = dom('[name="x5step"]').attr.value

        url = 'https://cf.aliyun.com/nocaptcha/analyze.jsonp'
        others = headers_raw_to_dict("""
            p: {"ncSessionID":"5e701f18a9c2"}
            scene: register
            asyn: 0
            lang: zh-tw
            v: 948
            callback: jsonp_04602644376803049
            """)

        parse_url = url_add_params(url, a=a, t=t, n=n, **others)
        web.get(parse_url)
        web.implicitly_wait(10)
        doc = web.page_source
        js = json.loads(re.findall('{.+}', doc)[0])
        print(js['result']['value'])
        print()
        # url = 'https://www.lazada.co.th/shop-smart-tracking/?ajax=True&page=1'
    # r = session.get(url,headers=headers_raw_to_dict("""
    # accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
    # accept-encoding: gzip, deflate, br
    # accept-language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
    # upgrade-insecure-requests: 1
    # user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36
    # """))
    # doc = r.content.decode()
    dom = pq(doc)
    t = dom('[name="nc_token"]').attr.value
    a = re.findall('appkey: "(.+?)",', doc)[0]

    get_url_query_str(parse_url)
    r = session.get(parse_url, headers=headers_raw_to_dict("""
    Referer: https://www.lazada.co.th/shop-smart-tracking/?ajax=True&page=1
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36
    """))

    js = json.loads(re.findall('{.+}', r.content.decode())[0])
    print(js['result']['value'])
    print()
