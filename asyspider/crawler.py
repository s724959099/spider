from collections import defaultdict, deque
from async_generator import asynccontextmanager
import hashlib
import inspect
import re
import attr
import functools
from .asyncrunner import AsyncRunner
from .fetcher import Fetcher
from .agent import get_agent
import logging
import time
from .proxy import Proxy

logger = logging.getLogger(__name__)
now = lambda: time.time()


@attr.s
class BaseArg:

    def items(self):
        keys = self.__dict__.keys()
        for key in keys:
            yield key, getattr(self, key)

    @classmethod
    @functools.lru_cache(maxsize=1)
    def attrs(cls):
        attr_str = str(cls.__attrs_attrs__)
        keys = re.findall("name=\'(.+?)\'", attr_str)

        return keys

    @classmethod
    def split_dict(cls, **kwargs):
        d1 = {}
        d2 = {}
        keys = cls.attrs()
        for key, val in kwargs.items():
            d = d1 if key in keys else d2
            d[key] = val

        return d1, d2


@attr.s
class CrawlArg(BaseArg):
    url = attr.ib()
    params = attr.ib(default=None)
    data = attr.ib(default=None)
    method = attr.ib(default='get')
    callback = attr.ib(default=None)
    task_id = attr.ib(default=None)
    read = attr.ib(default=True)
    referer = attr.ib(default=None)
    headers = attr.ib(default=None)
    # for callback args
    kwargs = attr.ib(default=attr.Factory(dict))


CrawlArg_KEY = CrawlArg.attrs()


class Crawler:
    check_crawled_urls = True
    proxy = True
    max_tasks = 1
    retries = 10
    allow_redirects = True
    timeout = 10
    sleep_time = 1
    update_cookies = True
    agent_type = 'desktop'
    fail_try_num = 3
    try_fail_time = 60 * 5
    headers = """
    accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
    accept-encoding: gzip, deflate, br
    accept-language: zh-TW,zh;q=0.9,en;q=0.8,zh-CN;q=0.7,en-US;q=0.6
    cache-control: no-cache
    pragma: no-cache
    upgrade-insecure-requests: 1
    """

    def __init__(self):
        self.crawled_urls = set()
        self.agent = get_agent(self.agent_type)
        self.proxy_instance = Proxy() if self.proxy else None

        self.__fails = deque()
        self.__fails_count = defaultdict(int)
        self.__runner = AsyncRunner(self)
        self.__fetcher = Fetcher(self)
        self.__total_urls = 0

    def on_start(self):
        pass

    def on_done(self):
        pass

    @functools.lru_cache(maxsize=2048)
    def __get_md5(self, data):
        m = hashlib.md5()
        m.update(data.encode())
        return m.hexdigest()

    def __url_params_to_str(self, data):
        if data is None or not len(data):
            return '*'
        else:
            return str(data)

    def __gen_task_id(self, crawl_arg):
        str_url = crawl_arg.url + \
                  self.__url_params_to_str(crawl_arg.params) + self.__url_params_to_str(crawl_arg.data)
        md5_url = self.__get_md5(str_url)
        crawl_arg.task_id = md5_url

    def __crawl_checking(self, *args, **kwargs):
        data, other_kwargs = CrawlArg.split_dict(**kwargs)
        crawl_arg = CrawlArg(*args, **data)
        if not crawl_arg.url.startswith('http'):
            return None
        crawl_arg.other_kwargs = other_kwargs
        if crawl_arg.task_id is None:
            self.__gen_task_id(crawl_arg)
        if self.check_crawled_urls:

            if crawl_arg.task_id in self.crawled_urls:
                logger.debug("repeated url: %s %s %s", crawl_arg.url, crawl_arg.params, crawl_arg.data)
                return None
            self.crawled_urls.add(crawl_arg.task_id)

        self.__total_urls += 1
        return crawl_arg

    def crawl(self, *args, **kwargs):
        crawl_arg = self.__crawl_checking(*args, **kwargs)
        if crawl_arg:
            self.__runner.add_task(crawl_arg)

    def add_task(self, **kwargs):
        self.__runner.add_task(kwargs)

    @asynccontextmanager
    async def fetch(self, *args, **kwargs):
        crawl_arg = self.__crawl_checking(*args, **kwargs)
        async with self.__fetcher.call_fetch(crawl_arg) as resp:
            resp.data = crawl_arg
            yield resp

    async def __crawl(self, crawl_arg):
        retries = self.retries
        status = None
        ret = None

        try:
            async with self.__fetcher.fetch(crawl_arg) as resp:
                if not resp:
                    pass
                else:
                    if crawl_arg.read:
                        ret = await resp.read()
                    resp.data = ret
                    return resp
        except Exception as e:
            logger.exception('__crawl error:')
            return None

    def __try_fails(self):
        if not len(self.__fails):
            return
        now_time = now()
        crawl_arg = self.__fails[0]

        if self.__fails_count[crawl_arg.task_id] <= self.fail_try_num and \
                now_time - crawl_arg.now >= self.try_fail_time:
            self.__runner.add_task(crawl_arg)
            self.__fails.popleft()

    def first_try_fails(self):
        while len(self.__fails):
            crawl_arg = self.__fails.popleft()
            self.__runner.add_task(crawl_arg)

    def still_fails_process(self):
        # todo not impl
        pass
        # record still failed
        # for i, d in enumerate(self.__fails):
        #     fail_log.info(d)

    def to_fails(self, crawl_arg):
        logger.warning("fails: %s %s", crawl_arg.url, crawl_arg.params)
        if crawl_arg in self.__fails:
            self.__fails.remove(crawl_arg)
        crawl_arg.now = now()
        self.__fails.append(crawl_arg)
        self.__fails_count[crawl_arg.task_id] += 1

    async def work(self, arg):
        self.__try_fails()
        if isinstance(arg, CrawlArg):
            ret = await self.__crawl(arg)
            if not ret:
                logger.warning('crawl None url: %s', arg.url)
                self.to_fails(arg)
                return
            ret.info = arg
            arg.callback(ret, **arg.kwargs) if not inspect.iscoroutinefunction(arg.callback) \
                else await arg.callback(ret, **arg.kwargs)
        else:
            callback = arg.get('callback')
            if callback:
                callback(**arg.get('kwargs', {})) if not inspect.iscoroutinefunction(callback) \
                    else await callback(**arg.get('kwargs', {}))

    def run(self, callback=None):
        """
        finnaly 最後執行的function
        """
        self.__runner.run(callback)

    def download(self, url, file_name, headers=None, download_part=20):
        headers = headers or self.headers
        self.crawl(url, callback=self.get_download_content, headers=headers,
                   read=False,
                   kwargs=(
                       dict(file_name=file_name,
                            headers=headers,
                            download_part=download_part)))

    def get_download_content(self, r, file_name, headers=None, download_part=20):
        file_size = int(r.headers['Content-Length'])
        logger.info('file: %s size: %s', file_name, file_size)
        fp = open(file_name, "wb")
        fp.truncate(file_size)
        fp.close()

        part = file_size // download_part
        get_headers = headers or self.headers
        for i in range(download_part):
            start = part * i
            if i == download_part - 1:
                end = file_size
            else:
                end = start + part

            task_headers = get_headers + """
            Range: bytes={}-{}
            """.format(start, end)
            self.add_task(callback=self.part_download, kwargs=dict(
                start=start, end=end, file_name=file_name,
                url=r.info.url, headers=task_headers,
            ))

    async def part_download(self, url, headers, start, end, file_name):
        logger.info('read: %s start: %s end:%s', file_name, start, end)
        async with self.fetch(url, headers=headers)as r:
            with open(file_name, "r+b") as fp:
                fp.seek(start)
                async for chunk in r.content.iter_chunked(1024000):
                    if chunk:
                        fp.write(chunk)


if __name__ == '__main__':
    pass
