#!/Users/Admin/anaconda3/envs/py36-anaconda/bin/python python
import requests
from pprint import pprint as pp
from pyquery import PyQuery as pq
import re
from urllib.parse import urljoin
from collections import OrderedDict
import time
import datetime

sess = requests.Session()
HOST = 'https://www.myfone.com.tw/buy/'


def str2digital(price, fn=int):
    return fn(re.sub('\D', '', price))


def find_items(off=0.5, discount_limit=2):
    url = 'https://www.myfone.com.tw/buy/main.php?action=supersale_list&preview=2&sort=0'
    r = sess.get(url)
    dom = pq(r.content.decode('utf-8'))
    found = False
    print("--------------start--------------")
    for el in dom('.product-list-inner-box').items():
        oprice = str2digital(el('del').text())
        nprice = str2digital(el('h3>strong').text())
        calc_off = round(1 - (nprice / oprice), 2)
        discount_str = el('.col-xs-5').text()
        discount_num = str2digital(discount_str)
        title = el('h2>a:eq(0)').text()
        url = urljoin(HOST, el('[target="_self"]:eq(0)').attr.href)
        if any([discount_limit >= discount_num, calc_off >= off]):
            print("%s %s %s $%s/$%s=%s  \nurl: %s" % (
                datetime.datetime.now().strftime('%H:%M'), title, discount_str, oprice, nprice, calc_off, url))
            found = True
    if not found:
        print('not found')


find_items(off=0.8, discount_limit=1)
while True:
    time.sleep(60 * 1)
    if datetime.datetime.now().minute % 15 == 0:
        find_items(off=0.8, discount_limit=1)
