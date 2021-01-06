import concurrent.futures
import logging
import asyncio
import inspect
import requests
import threading
import async_timeout
import functools
import time
import hashlib
# from tinydb import TinyDB, Query
import random
import os

try:
    from . import agent
except ImportError as e:
    import agent

# db = TinyDB(os.path.join(os.path.dirname(__file__), './db.json'))
# Proxies = db.table('Proxies')
# query = Query()

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

requests.packages.urllib3.disable_warnings()
logger = logging.getLogger('fetcher')


class FetchBase:

    def reset(self):
        pass

    async def fetch(self, url, method='GET', *args, **kwargs):
        pass


class HTTPAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.rlock = threading.RLock()
        super().__init__(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        self.rlock.acquire()
        r = None
        try:
            r = super().proxy_manager_for(*args, **kwargs)
        except Exception as e:
            logger.exeption('HTTPAdapter')
        self.rlock.release()
        return r


class RequestsFetcher(FetchBase):
    def __init__(self, *args, **kwargs):
        self.session = requests.session()
        self.session.mount('https://', HTTPAdapter(pool_maxsize=kwargs.get('max_tasks', 40)))
        self.session.mount('http://', HTTPAdapter(pool_maxsize=kwargs.get('max_tasks', 40)))
        if 'max_tasks' in kwargs:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=kwargs['max_tasks'])
        else:
            self.executor = concurrent.futures.ThreadPoolExecutor()

    async def fetch(self, url, method='GET', fetch_args=None, rjson=None):
        fetch_method = self.session.get if method == 'GET' else self.session.post
        ioloop = asyncio.get_event_loop()
        r = await ioloop.run_in_executor(self.executor, functools.partial(fetch_method, url, **fetch_args))
        r.result = r.json() if rjson else r.content
        return r

    def reset(self):
        self.session = requests.session()
        self.session.mount('https://', HTTPAdapter())
        self.session.mount('http://', HTTPAdapter())


class AiohttpFetcher(FetchBase):
    def __init__(self, *args, **kwargs):
        if 'max_tasks' in kwargs:
            self.connector = aiohttp.TCPConnector(limit=kwargs['max_tasks'])
        else:
            self.connector = aiohttp.TCPConnector()
        self.connector = aiohttp.TCPConnector()
        self.session = aiohttp.ClientSession(connector=self.connector)

    def fetch_args_adapter(self, fetch_args):
        fetch_args['proxy'] = fetch_args.get('proxies').get('http')
        del fetch_args['proxies']
        fetch_args['verify_ssl'] = fetch_args['verify']
        del fetch_args['verify']
        return fetch_args

    async def fetch(self, url, method='GET', fetch_args=None, rjson=None):
        fetch_args = self.fetch_args_adapter(fetch_args)
        fetch_method = self.session.get if method == 'GET' else self.session.post
        async with fetch_method(url, **fetch_args) as r:
            r.status_code = r.status
            r.result = await r.json() if rjson else await r.read()
            return r

    def reset(self):
        self.session.detach()
        if 'max_tasks' in kwargs:
            self.connector = aiohttp.TCPConnector(limit=kwargs['max_tasks'])
        else:
            self.connector = aiohttp.TCPConnector()
        self.session = aiohttp.ClientSession(connector=self.connector)


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


class Proxy:

    @classmethod
    def get_proxies(cls, *args, **kwargs):
        return {}

    @classmethod
    def update_proxies(cls, proxies):
        pass


class DBProxy(Proxy):
    dead_proxies = []

    @classmethod
    def get_proxies(cls, *args, **kwargs):
        proxies = Proxies.all()
        http = None
        ret = {}
        for _i in range(50):
            p = random.choice(proxies)
            http = "{}:{}".format(p['ip'], p['port'])
            if cls.dead_proxies.count(http) < 3:
                break
        else:
            logger.warning('try more 50')
        if http:
            ret = dict(http=http, https=http)
        return ret

    @classmethod
    def update_proxies(cls, proxies):
        cls.dead_proxies.append(proxies.get('http', ''))
        if len(cls.dead_proxies) > 100:
            cls.dead_proxies.pop(0)


class Cookie:
    __data_dict = dict()
    cookie_length = 3000

    def reset(self):
        self.__data_dict = dict()

    def update(self, cookie=None):
        """
        example
        cookie="gsScrollPos-1797=0; ASPSESSIONIDACBACDBR=HDCGLPNAPCEEFILBOONBMLFM; JCKin=0; JCCnt=0; ASP.NET_SessionId=acwz3tuz2zmgadlb1spdfh1x; _ga=GA1.2.1175740341.1530513766; _gid=GA1.2.719574033.1530513766; ASPSESSIONIDCABDBDBR=HEKNLGOAPKCHOFBGBNPAJMCO; __utmc=142350377; __utmz=142350377.1530516763.1.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none); ASPSESSIONIDACBBDCAR=HFAOMEPAHAKFLLCIIPEBKDGK; ASPSESSIONIDQQCCTCSS=DFHJIFGBGKDDKEKPPOJCLGCP; JUqCk=; JPcCk=; langNum=3; CookieLanguageActiveID=3; langNumID=ch; ASPSESSIONIDQQCCTCTS=ONIIKEIBFHBPGJCNNADCIBCI; looyu_id=e2533aad8dece3225a52c94054b431da64_20002049%3A2; looyu_20002049=v%3A99f06fc516a29a5c890f102c736a6b2d7e%2Cref%3A%2Cr%3A%2Cmon%3Ahttp%3A//m2423.talk99.cn/monitor%2Cp0%3Ahttp%253A//www.jshoppers.com/ch/shohin.asp%253Fshocd%253DW08453; _99_mon=%5B0%2C0%2C0%5D; cmbbrd=; ck%5Fph%5Fcatego=1; __utma=142350377.1201365579.1530516763.1530524042.1530608964.3; __utmb=142350377; JUserCk=0"
        """
        if isinstance(cookie, str):
            self.__udpate_str(cookie)
        if isinstance(cookie, dict):
            self.__update_dict(cookie)
        if isinstance(cookie, requests.cookies.RequestsCookieJar):
            d = cookie.get_dict()
            for key, val in d.items():
                self.__data_dict[key.strip()] = val.strip()

    def over_cookie_length_execute(self, ret):
        """
        default is reset
        you can overwrite it
        """
        self.reset()

    def to_header(self, retries=3):
        result = []
        for key, val in self.__data_dict.items():
            result.append("{}={}".format(key.strip(), val).strip())
        if len(result):
            ret = ";".join(result)
        else:
            ret = ""
        if len(ret) > self.cookie_length:
            if retries:
                self.over_cookie_length_execute(ret)
                return self.to_header(retries=retries - 1)
            else:
                logger.warning('cookie len: %s', len(ret))

        return ret

    def __update_to_data(self, cookie_str):
        if not len(cookie_str):
            return
        key, val = cookie_str.split('=', 1)
        key, val = key.strip(), val.strip()
        key, val = key.strip(';'), val.strip(';')
        self.__data_dict[key] = val

    def __udpate_str(self, cookie):
        if not len(cookie):
            return
        if cookie[-1] != ';':
            cookie += ';'
        datas = re.findall(".+?=.+?;", cookie.replace('Set-Cookie:', ''))
        for data in datas:
            self.__update_to_data(data)

    def __update_dict(self, cookie):
        """
        example cookie
        cookie = {
            'ASPSESSIONIDACRCASCD': 'Set-Cookie: ASPSESSIONIDACRCASCD=KJCANPACKPGACILJIHAMPOLL; Domain=www.jshoppers.com; Path=/'}
        """
        for key, val in cookie.items():
            val = str(val)
            data = re.findall(".+?=.+?;", val.replace('Set-Cookie:', ''))
            store_cookie_str = data[0]
            self.__update_to_data(store_cookie_str)


class FetcherWrapper:
    __display_fetch_times = 0

    def __init__(self, fetcher, crawler):
        self.fetcher = fetcher
        self.crawler = crawler
        self.cookie = Cookie()
        self.infos = dict(
            fetch_times=0, fetch_fail_times=0, try_fetch_total=0, try_fetch_fail_total=0, total_spend_sec=0
        )

    def args_preprocess(self, *args, **kwargs):
        # preprocess kwargs
        if not kwargs.get('headers'):
            kwargs['headers'] = self.crawler.headers
        if isinstance(kwargs.get('headers', {}), str):
            kwargs['headers'] = headers_raw_to_dict(kwargs.get('headers'))
        headers = {**kwargs.get('headers', {})}
        pt = self.crawler.platform
        if kwargs.get('platform'):
            pt = kwargs.get('platform')
            del kwargs['platform']
        if 'user-agent' not in headers:
            user_agent = agent.random_agent(platform=pt)
            headers['user-agent'] = user_agent
        referer = None
        if kwargs.get('referer'):
            referer = kwargs.get('referer')
            del kwargs['referer']
        if referer and 'referer' not in headers:
            headers['referer'] = referer
        return headers

    async def fetch(self, url, method='GET', *args, **kwargs):
        time_start = time.time()
        r = await self.__fetch(url, method=method, *args, **kwargs)
        spend_time = time.time() - time_start
        logger.debug('spend time: %.2f fetch %s', spend_time, url)

        self.infos['total_spend_sec'] += spend_time

        if self.infos['fetch_times'] // 100 > self.__display_fetch_times:
            self.__display_fetch_times = self.infos['fetch_times'] // 100
            logger.info('AVG spend time: %.2f fetch_times: %s try_total: %s try_fail: %s',
                        self.infos['total_spend_sec'] / self.infos['fetch_times'],
                        self.infos['fetch_times'],
                        self.infos['try_fetch_total'],
                        self.infos['try_fetch_fail_total'],
                        )
        return r

    async def __fetch(self, url, method='GET', *args, **kwargs):
        if isinstance(kwargs.get('headers', {}), str):
            kwargs['headers'] = headers_raw_to_dict(kwargs.get('headers'))
        self.infos['fetch_times'] += 1
        r = None
        try_success = False
        for retry_count in range(self.crawler.retries):
            proxies = kwargs.get('proxies', self.crawler.ProxyClass.get_proxies(*args, **kwargs))
            self.infos['try_fetch_total'] += 1
            headers = self.args_preprocess(*args, **kwargs)
            r = None
            bot_args = dict(
                headers=headers,
                proxies=proxies,
                verify=False,
                allow_redirects=kwargs.get('allow_redirects', True),
                params=kwargs.get('params', {}),
                timeout=self.crawler.timeout
            )
            if 'content-type' in headers and 'json' in headers['content-type']:
                bot_args['json'] = kwargs.get('data')
            else:
                bot_args['data'] = kwargs.get('data')

            try:
                async with async_timeout.timeout(
                        self.crawler.timeout):
                    r = await self.fetcher.fetch(url, method, bot_args, kwargs.get('rjson', False))
                    __cookie = r.cookies
                    if self.crawler.update_cookies and __cookie:
                        self.cookie.update(__cookie)
                    status_code = r.status_code
                    if r.status_code not in self.crawler.status_code:
                        logger.info('get status: %s url: %s', r.status_code, url)
                        continue
                    content = r.result
                    if ((kwargs.get('rjson', False) or len(content) > self.crawler.min_content_length) and
                            self.crawler.fetch_check(r)):
                        urlcontent = content
                        try_success = True
                        break
            except Exception as inst:
                logger.debug('try fail: %s', url)
                self.infos['try_fetch_fail_total'] += 1
                self.crawler.ProxyClass.update_proxies(proxies)
                if self.crawler.sleep_time:
                    await asyncio.sleep(self.crawler.sleep_time)
        if not try_success:
            self.infos['fetch_fail_times'] += 1
        return r


class Spider:
    status_code = (200, 301, 302)
    platform = 'desktop'
    max_tasks = 1
    sleep_time = None
    timeout = 90
    retries = 10
    check_crawled_urls = True
    update_cookies = True
    min_content_length = 1
    FetcherClass = RequestsFetcher
    ProxyClass = Proxy
    headers = """
    accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
    accept-encoding: gzip, deflate, br
    accept-language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
    cache-control: no-cache
    pragma: no-cache
    upgrade-insecure-requests: 1
    """
    crawled_urls = set()

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.fetcher = FetcherWrapper(
            self.FetcherClass(max_tasks=self.max_tasks),
            crawler=self

        )

    def finally_work(self):
        """寫給繼承用的 結束要做的事情"""
        pass

    def on_end(self):
        """結束"""
        pass

    def on_start(self):
        """最一開始"""
        pass

    def work_exception(self):
        """每一個task 失敗後要做的事情"""
        pass

    def fetch_check(self, r):
        """最後驗證要不要通過"""
        return True

    @functools.lru_cache(maxsize=2048)
    def get_md5(self, data):
        m = hashlib.md5()
        m.update(data.encode())
        return m.hexdigest()

    def __url_params_to_str(self, data):
        if data is None or not len(data):
            return '*'
        else:
            return str(data)

    def __crawl_checking(self, *args, **kwargs):
        """
        在crawl or asyn_crawl之前先做前處理
        判斷是否爬過
        :return crawl_arg or None
        """
        url = kwargs.get('url')
        params = kwargs.get('params')
        data = kwargs.get('data')
        if not url.startswith('http'):
            logger.warning('url not start with http: %s', url)
            return False
        if kwargs.get('check_crawled_urls', self.check_crawled_urls):
            str_url = url + \
                      self.__url_params_to_str(params) + self.__url_params_to_str(data)
            md5_url = self.get_md5(str_url)

            if md5_url in self.crawled_urls:
                logger.debug("repeated url: %s %s %s", url, params, data)
                return False
            self.crawled_urls.add(md5_url)
        return True

    async def async_crawl(self, url, method='GET', *args, **kwargs):
        r = None
        if self.__crawl_checking(url=url, **kwargs):
            r = await self.fetcher.fetch(url, method=method, *args, **kwargs)
        return r

    def add_task(self, callback, *args, **kwargs):
        self.queue.put_nowait((callback, args, kwargs))

    async def __run_async_work(self):
        workers = [
            asyncio.Task(self.__worker(i), loop=self.loop)
            for i in range(self.max_tasks)
        ]
        self.add_task(self.on_start)
        await self.queue.join()

        for worker in workers:
            worker.cancel()

    async def execute_fn(self, fn, *args, **kwargs):
        """
        不論coroutinefunction or 一般function 都可以執行
        """
        if inspect.iscoroutinefunction(fn):
            ret = await fn(*args, **kwargs)
        else:
            ret = fn(*args, **kwargs)
        return ret

    async def __worker(self, i):
        while True:
            try:
                callback, args, kwargs = await self.queue.get()
                await self.execute_fn(callback, *args, **kwargs)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception('work exception')
                await self.execute_fn(self.work_exception)
                self.queue.task_done()
            finally:
                pass

    def run(self):
        logger.info('use task: %s', self.max_tasks)
        try:
            self.loop.run_until_complete(self.__run_async_work())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        except asyncio.CancelledError:
            logging.warning("cancel error")
        except Exception as e:
            logger.exception('run done error')
        finally:
            self.on_end()
            self.finally_work()
