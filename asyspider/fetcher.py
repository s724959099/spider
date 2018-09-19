import logging
import aiohttp
import asyncio
import async_timeout
import re
from async_generator import asynccontextmanager
from .proxyhandler import ProxyHandler
from .agent import get_agent

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


class HeaderHandler:

    def __init__(self, agent_type='desktop', update_cookies=True):
        self.agent_type = agent_type
        self.cookie = Cookie() if update_cookies else None

    def handle_headers(self, headers, referer=None, update_cookies=True):
        if headers is None:
            headers = dict()
        if isinstance(headers, str):
            headers = headers_raw_to_dict(headers)
        # update cookie
        if self.cookie:
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
        header_lower_keys = list(map(lambda x: x.lower(), headers.keys()))
        if 'user-agent' not in header_lower_keys:
            headers['user-agent'] = get_agent(self.agent_type)
        if referer and 'referer' not in header_lower_keys:
            headers['Referer'] = referer
        return headers

    def update_cookie(self, cookie):
        if not self.cookie:
            return
        self.cookie.update(cookie)


class Fetcher:

    def __init__(self, crawler):
        self.crawler = crawler
        self.headerhandler = HeaderHandler(self.crawler.agent_type, self.crawler.update_cookies)

    @asynccontextmanager
    async def fetch(self, crawl_arg):
        fetch_headers = self.headerhandler.handle_headers(crawl_arg.headers)
        crawl_arg.fetch_headers = fetch_headers
        method_args = dict(
            url=crawl_arg.url,
            headers=fetch_headers,
            proxy="http://{}".format(crawl_arg.proxy.get('key')) if crawl_arg.proxy else None,
            verify_ssl=False,
            allow_redirects=self.crawler.allow_redirects,
            params=crawl_arg.params,
            data=crawl_arg.data,
            timeout=self.crawler.timeout
        )
        async with aiohttp.ClientSession() as session:
            fetch_method = getattr(session, crawl_arg.method)
            async with fetch_method(**method_args) as resp:
                if not resp:
                    yield
                else:
                    if not (resp.status in [200, 201, 206] or resp.reason == 'OK'):
                        logger.error('status not 200: %s %s' % (resp.status, crawl_arg.url))
                    __cookie = resp.cookies
                    if __cookie:
                        self.headerhandler.update_cookie(__cookie)
                    yield resp
