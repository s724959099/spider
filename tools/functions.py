from urllib.parse import parse_qsl, parse_qs, urlsplit, urlencode
from contextlib import contextmanager
import os
import sys
import time
import logging
from functools import wraps, partial
import inspect
import requests
import asyncio


def wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run


class Wrapper:
    pass


def aiowrap(obj):
    if callable(obj):
        return wrap(obj)
    elif inspect.ismodule(obj) or inspect.isclass(obj):
        wrapped_obj = Wrapper()
        try:
            if getattr(obj, '__all__'):
                attrnames = obj.__all__
            else:
                attrnames = dir(obj)
        except Exception as e:
            attrnames = dir(obj)

        for attrname in attrnames:
            if attrname.startswith('__'):
                continue
            original_obj = getattr(obj, attrname)
            setattr(wrapped_obj, attrname, aiowrap(original_obj))
        return wrapped_obj
    else:
        return obj


logger = logging.getLogger('functions')


def asynctry_safe(fetch_type='async_crawl'):
    """
    被裝飾的method可以使用crawl 呼叫method or 直接傳url 呼叫 method
    並且該method 會包裝try catch 如果錯誤 顯示錯誤的url
    example:
    call function
    await self.pages_preprocess(url, fetch_kwargs=dict(
                headers=self.get_headers(url)
            ))

    @asynctry_safe
    async def pages_preprocess(self, r):
    --or--
    @asynctry_safe(fetch_type='reachurl')
    async def pages_preprocess(self, r):
    """

    def outside(fn):
        @wraps(fn)
        async def wrapper(self, url, *args, **kwargs):
            ret = None
            fetch_methods = dict(
                async_crawl=self.async_crawl,
                reachurl=self.auc.reachurl
            )
            fetch_kwargs = kwargs.get('fetch_kwargs', dict())
            if 'fetch_kwargs' in kwargs:
                del kwargs['fetch_kwargs']
            try:
                if isinstance(url, str) and url.startswith('http'):
                    r = await fetch_methods[fetch_type](url, **fetch_kwargs)
                    if not r:
                        return ret
                else:
                    r = url
                    url = r.info.url
                ret = await fn(self, r, *args, **kwargs)
            except Exception as e:
                logger.exception('error url: %s', url)

            return ret

        return wrapper

    if callable(fetch_type):
        fn = fetch_type
        fetch_type = 'async_crawl'
        return outside(fn)
    else:
        return outside


def get_url_query_str(url):
    """
    >> get_url_query_str(url)
    {'item': '98', 'ct': '32', 'op': '92'}
    """
    split_result = urlsplit(url)
    return dict(parse_qsl(split_result.query))


def url_with_query_str(url, *args, **kwargs):
    """
    >> url_with_query_str(url2,d)
    >> url_with_query_str(url2,item=3)
    'http://www.example.org/default.html?item=98&ct=32&op=92'
    'http://www.example.org/default.html?item=3'

    """
    if len(args):
        d = args[0]
    elif len(kwargs):
        d = kwargs
    else:
        raise Exception('not found dict')
    if any("%" in k for k in d.keys()):
        query = "&".join(["{}={}".format(k, v) for k, v in d.items()])
    else:
        query = urlencode(d)
    url = url.split('?')[0]
    return "{}?{}".format(url, query)


def url_add_params(url, *args, **kwargs):
    if len(args):
        d = args[0]
    elif len(kwargs):
        d = kwargs
    else:
        raise Exception('not found dict')
    params = get_url_query_str(url)
    params.update(d)
    return url_with_query_str(url, params)


def find_dict_to_list(target, pattern):
    """
    find any sub dict contains pattern to list
    :return result
    """
    result = []
    if isinstance(target, dict):
        for k, v in target.items():
            if k == pattern:
                result.append(v)
            if isinstance(v, dict) or isinstance(v, list):
                result.extend(find_dict_to_list(v, pattern))
    if isinstance(target, list):
        for data in target:
            if isinstance(data, dict) or isinstance(data, list):
                result.extend(find_dict_to_list(data, pattern))
    return result


def url_merge(start, end):
    assert "?" not in start
    if start.endswith('/') and end.startswith('/'):
        end = end[1::]
    if not start.endswith('/') and not end.startswith('/'):
        end = "/" + end
    return start + end


@contextmanager
def try_safety():
    """
    >> page_count = 1
    >> with try_safety():
    >>     page_count = max([])
    :return:
    """
    try:
        yield
    except Exception as e:
        pass


def el_selector(*args):
    for el in args:
        if el:
            return el


class CurrencyRate:
    """
    all currency:'USD','MWK','BYN','RSD','STD','BRX','UGX','PGK','LSL','ZMW','MRO','BWP','TZS','XAF','TWD','SDG','FRF','BAM','UYU','MRU','CZK','XCD','GGP','ERN','HTG','HRK','MMK','BIF','TTD','LYD','OMR','IDR','MAD','BBD','EUR','LBP','TND','MOP','UAH','SVC','GBP','NGN','ALL','GTQ','JMD','LTC','MZN','XPF','MYR','DEM','BSD','MDL','SYP','KRW','SBD','AMD','XOF','GHS','GMD','RUB','THB','PHP','KYD','LVL','CRC','GNF','EGP','ISK','SOS','ECS','FKP','YER','XAU','LTL','MXN','SIT','RWF','SGD','DZD','AWG','SRD','SHP','MNT','XPT','BDT','COP','DJF','TJS','SZL','BYR','PYG','AZN','MVR','ARS','CLP','AOA','LKR','INR','CNY','JPY','MKD','LAK','TRY','CAD','HUX','AED','VUV','NOK','PKR','GYD','MGA','DKK','SEK','BOB','BTC','ANG','IRR','VEF','BGN','CUP','KES','XPD','WST','QAR','CLF','PEN','LRD','HNL','SSP','KZT','JOD','KHR','PAB','AFN','NAD','TOP','KWD','CNH','AUD','MXV','GEL','DOGE','XAG','PLN','KGS','FJD','ZAR','TMT','BMD','DOP','JEP','NZD','HUF','CDF','HKD','SAR','ZWL','IQD','KMF','IMP','MUR','SCR','CUC','VES','CHF','ETB','BHD','CVE','GIP','NPR','BTN','NIO','VND','XDR','ITL','USD','KPW','RON','BND','BZD','STN','SLL','ILS','BRL','UZS','IEP'

    example
    currency = Currency('usd', 'TWD')
    price = currency.change("20")
    currency = Currency('usd', 'USDTWD')
    price = currency.change(3.5)
    """

    def __init__(self, from_, to):
        """
        allow lower string and ellipsis USD
        """
        r = requests.get('https://tw.rter.info/capi.php?api=HIeh22KXrDg')
        self.data = r.json()
        self.set_locations(from_, to)

    def set_locations(self, from_, to):
        str_check = lambda x: 'USD{}'.format(x.upper()) if 'USD' not in x.upper() else x.upper()
        from_ = str_check(from_)
        to = str_check(to)
        try:
            assert from_ in self.data
            assert to in self.data
        except Exception as e:
            raise Exception('dollar list: %s' % list(self.data.keys()))

        self.from_ = from_
        self.to = to

    def change(self, price):
        price = float(price)
        return price * self.data[self.to]['Exrate'] / self.data[self.from_]['Exrate']


def send_email(content='', title='Example test', to='max@funmula.com'):
    from email.message import EmailMessage
    from datetime import datetime
    import smtplib
    import json

    try:
        msg = EmailMessage()
        msg.set_content(content, subtype='html')
        msg['Subject'] = title + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg['From'] = 'service@funmula.com'
        msg['To'] = to

        smtp_config = {
            "server": "localhost",
            "port": 25
        }
        try:
            config_file = os.path.join(os.environ['HOME'], 'etc', 'smtp.json')
            with open(config_file) as fd:
                smtp_config = json.load(fd)
        except Exception as e:
            pass

        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as smtp:
            smtp.starttls()
            if 'user' in smtp_config and 'passwd' in smtp_config:
                smtp.login(smtp_config['user'], smtp_config['passwd'])
            smtp.send_message(msg)
    except Exception as e:
        logger.warning('send email fail', exc_info=True)


def thread_pool_exec(fn, datas, works=3):
    import concurrent.futures
    result = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=works) as executor:
        futuredict = {executor.submit(fn, d): d for d in datas}
        for future in concurrent.futures.as_completed(futuredict):
            args = futuredict[future]
            fresult = future.result()
            if fresult and args:
                result.append(fresult)

    return result


def __timeit_simple(method):
    lgr = logging.getLogger('timer')

    async def af(*args, **kw):
        ts = time.time()
        result = await method(*args, **kw)
        te = time.time()
        tspend = sec_to_time(te - ts)
        lgr.info('%r  %s args: %s kwargs: %s', method.__name__, tspend, args[1:], kw)
        return result

    def f(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        tspend = sec_to_time(te - ts)
        lgr.info('%r  %s args: %s kwargs: %s', method.__name__, tspend, args[1:], kw)
        return result

    if inspect.iscoroutinefunction(method):
        ret = af
    else:
        ret = f

    return ret


def timeit(*dargs, **dkwargs):
    def wrapper(method):
        # timeit args
        level = dkwargs.get('level', logging.INFO)

        lgr = logging.getLogger('timer')
        lgr_type = {
            logging.DEBUG: lgr.debug,
            logging.INFO: lgr.info,
            logging.WARNING: lgr.warning,
            logging.ERROR: lgr.error,
        }
        lgrmethod = lgr_type[level]

        async def af(*args, **kw):
            ts = time.time()
            result = await method(*args, **kw)
            te = time.time()
            tspend = sec_to_time(te - ts)
            lgrmethod('%r  %s args: %s kwargs: %s', method.__name__, tspend, args[1:], kw)
            return result

        def f(*args, **kw):
            ts = time.time()
            result = method(*args, **kw)
            te = time.time()
            tspend = sec_to_time(te - ts)
            lgrmethod('%r  %s args: %s kwargs: %s', method.__name__, tspend, args[1:], kw)
            return result

        if inspect.iscoroutinefunction(method):
            ret = af
        else:
            ret = f

        return ret

    # support both @timeit and @timeit(level=logging.DEBUG)....etc
    if len(dargs) == 1 and callable(dargs[0]):
        return __timeit_simple(dargs[0])
    else:
        return wrapper


def sec_to_time(sec):
    sec = int(sec)
    h = sec // (60 * 60)
    sec -= h * 60 * 60
    m = sec // 60
    sec -= m * 60
    return "{}:{:0>2d}:{:0>2d}".format(h, m, sec)


if __name__ == '__main__':
    @timeit()
    def demo(*args, **kwargs):
        print('demo', args, kwargs)
        time.sleep(1)


    demo()
