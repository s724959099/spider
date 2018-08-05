from collections import defaultdict, deque
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
    max_tasks = 1
    headers = None
    retries = 3
    allow_redirects = True
    timeout = 10
    sleep_time = 1
    update_cookies = True
    agent_type = 'desktop'
    fail_try_num = 3
    try_fail_time = 60 * 5

    def __init__(self):
        self.crawled_urls = set()
        self.agent = get_agent(self.agent_type)

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

    async def __crawl(self, crawl_arg):
        proxy = None
        retries = self.retries
        status = None
        ret = None

        try:
            async with self.__fetcher.fetch(crawl_arg, proxy) as resp:
                if crawl_arg.read and ret:
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
        for i, d in enumerate(self.__fails):
            fail_log.info(d)

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
                self.to_fails(arg)
            ret.info = arg
            arg.callback(ret, **arg.kwargs) if not inspect.iscoroutinefunction(arg.callback) \
                else await arg.callback(ret, **arg.kwargs)

    def run(self, callback=None):
        """
        finnaly 最後執行的function
        """
        self.__runner.run(callback)


if __name__ == '__main__':
    pass
