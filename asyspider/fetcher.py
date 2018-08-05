import logging
import aiohttp
import asyncio
import async_timeout
import re
from async_generator import asynccontextmanager

logger = logging.getLogger(__name__)


class Cookie:
    __data_dict = dict()

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

    def to_header(self):
        result = []
        for key, val in self.__data_dict.items():
            result.append("{}={}".format(key.strip(), val).strip())
        if len(result):
            return " ".join(result)
        else:
            return ""

    def __update_to_data(self, cookie_str):
        if not len(cookie_str):
            return
        key, val = cookie_str.split('=', 1)
        self.__data_dict[key] = val

    def __udpate_str(self, cookie):
        if not len(cookie):
            return
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


def try_wrapper(fn):
    @asynccontextmanager
    async def wrapper(self, crawl_arg, proxy):
        retries = self.crawler.retries
        sleep_time = self.crawler.sleep_time
        while retries:
            retries -= 1
            try:
                async with fn(self, crawl_arg, proxy) as resp:
                    yield resp
                    break
            except aiohttp.ClientError as e:
                logger.exception('ClientError')
            except asyncio.TimeoutError as e:
                logger.exception('TimoutError')
                await asyncio.sleep(sleep_time)
            except Exception as e:
                logger.exception('Exception')
                await asyncio.sleep(sleep_time)

    return wrapper


class Fetcher:
    def __init__(self, crawler):
        self.crawler = crawler
        self.cookie = Cookie()

    async def reset(self):
        self.cookie.reset()

    def handle_headers(self, crawl_arg):
        headers = crawl_arg.headers or self.crawler.headers
        if isinstance(headers, str):
            headers = headers_raw_to_dict(headers)
        referer = crawl_arg.referer
        # update cookie
        if self.crawler.update_cookies:
            cookie_str = "Cookie"
            cookie = None
            for s in "Cookie cookie".split():
                if headers.get(s):
                    cookie = headers.get(s)
                    cookie_str = s
                    break
            if cookie:
                self.cookie.update(cookie)
            cookie_header = self.cookie.to_header()
            if cookie_header:
                headers[cookie_str] = cookie_header

        # update others
        if 'User-Agent' not in headers and 'user-agent' not in headers:
            headers['user-agent'] = self.crawler.agent
        if referer and 'Referer' not in headers:
            headers['Referer'] = referer
        return headers

    @try_wrapper
    @asynccontextmanager
    async def call_fetch(self, crawl_arg, proxy):
        method_args = dict(
            url=crawl_arg.url,
            headers=self.handle_headers(crawl_arg),
            proxy=proxy,
            verify_ssl=False,
            allow_redirects=self.crawler.allow_redirects,
            params=crawl_arg.params,
            data=crawl_arg.data,
        )
        timeout = self.crawler.timeout
        async with async_timeout.timeout(
                timeout):
            async with aiohttp.ClientSession() as session:
                fetch_method = getattr(session, crawl_arg.method)
                async with fetch_method(**method_args) as resp:
                    yield resp

    @asynccontextmanager
    async def fetch(self, crawl_arg, proxy):
        async with self.call_fetch(crawl_arg, proxy) as resp:
            if not (resp.status == 200 or resp.reason == 'OK'):
                raise Exception('status not 200: %s', resp.status)
            __cookie = resp.cookies
            if __cookie:
                self.cookie.update(__cookie)
            yield resp
