import time
import re
import asyncio
import datetime
import inspect
import os
import logging
import random
from request_mixin import RequestMixin, aRequestMixin, headers_raw_to_dict, BaseArg
import requests
import hashlib
import functools
from collections import defaultdict, deque
import attr

logger = logging.getLogger(__name__)
try:
    from eslib import ees
except Exception as e:
    logger.warning('not found eslib module')
    ees = None

fail_log = logging.getLogger('abike_fails')
now = lambda: time.time()


def seconds_to_time(s):
    s = int(s)
    m = s // 60
    h = m // 60
    m = m - h * 60
    s = s - m * 60 - h * 60 * 60
    return "%02d:%02d:%02d" % (h, m, s)


class EasyDict(dict):
    def __init__(self, d=None, **kwargs):
        if d is None:
            d = {}
        if kwargs:
            d.update(**kwargs)
        for k, v in d.items():
            setattr(self, k, v)
        # Class attributes
        for k in self.__class__.__dict__.keys():
            if not (k.startswith('__') and k.endswith('__')):
                setattr(self, k, getattr(self, k))

    def __setattr__(self, name, value):
        if isinstance(value, (list, tuple)):
            value = [self.__class__(x)
                     if isinstance(x, dict) else x for x in value]
        elif isinstance(value, dict) and not isinstance(value, self.__class__):
            value = self.__class__(value)
        super(EasyDict, self).__setattr__(name, value)
        super(EasyDict, self).__setitem__(name, value)

    __setitem__ = __setattr__


class BaseCrawler:
    ees = ees

    def __init__(self):
        self.uc = Requesturl()
        self.i = 0
        self.keypool = {}
        self.esbuf = []
        self.spam_count = 0
        self.total = 0
        self.error_total = 0

    def __del__(self):
        self.syncesbuf()

    def getint(self, strtext):
        intstr = re.sub("[^0-9.]", "", strtext)
        if len(intstr) > 0:
            return int(float(intstr))
        else:
            return 0

    def getfloat(self, strtext):
        intstr = re.sub("[^0-9.]", "", strtext)
        if len(intstr) > 0:
            return float(intstr)
        else:
            return 0

    def syncesbuf(self):
        if len(self.esbuf) > 0:
            st = time.time()
            assert self.ees is not None
            ec = self.ees()
            for item in self.esbuf:
                ec.insert(item)
            ec.syncinsert()
            print('sync into es used time:', time.time() - st, ' seconds size:', len(self.esbuf))
            self.esbuf = []

    def append_buf(self, item):
        arr = self.esbuf
        arr.append(item)
        self.esbuf = arr
        self.i += 1
        if len(self.esbuf) >= 500:
            self.syncesbuf()

    def spamcheck(self, item):
        chk = False
        if item['url'] not in self.keypool or item['iid'] not in self.keypool:
            chk = True
            self.keypool[item['url']] = 1
            self.keypool[item['iid']] = 1
        else:
            # logger.debug("Spam: %s", item)
            pass

        if chk is False:
            self.spam_count += 1
            if self.show_spam:
                logger.debug("""spam check
from_url: %s
spam reason: %s
item: %s""",
                             item['from_url'],
                             'url' if item['url'] in self.keypool else 'iid',
                             item)

        return chk


@attr.s
class CrawlArg(BaseArg):
    url = attr.ib()
    params = attr.ib(default=None)
    data = attr.ib(default=None)
    method = attr.ib(default='GET')
    callback = attr.ib(default=None)
    task_id = attr.ib(default=None)
    # for callback args
    kwargs = attr.ib(default=attr.Factory(dict))


CrawlArg_KEY = CrawlArg.attrs()


# TODO check_crawled_urls 遇到params不同但是url相同的會跳過
class AioBaseCrawler(BaseCrawler):
    max_tasks = 10
    try_fail_time = 60 * 5
    timeout = 10
    sleep_time = None
    headers = None
    start_urls = []  # first urls
    proxy_kwargs = {
        'foreign': True
    }
    retries = 3
    DEBUG = True
    check_crawled_urls = True
    show_spam = False
    update_cookies = True
    fail_try_num = 3
    auto_validate_fail = True

    # 不可設定參數
    __fails = deque()
    # 計算fails 次數
    __fails_count = defaultdict(int)
    _loop = asyncio.get_event_loop()
    _tasks_que = asyncio.Queue(loop=_loop)
    __total_urls = 0
    __total_crawled = 0
    AsyncRequesturl = aRequestMixin

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.crawled_urls = set()
        self.i = 0
        self.keypool = {}
        self.esbuf = []
        self.spam_count = 0
        self.total = 0
        self.error_total = 0

        # get all attr key for init uc and auc
        all_keys = list(vars(self).keys())
        for key in vars(AioBaseCrawler).keys():
            if not key.startswith('_'):
                all_keys.append(key)
        init_kwargs = {key: getattr(self, key) for key in all_keys}
        self.auc = self.AsyncRequesturl(**init_kwargs)

    def __del__(self):
        self.syncesbuf()
        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(self.delete(loop))
        # loop.close()

    async def delete(self, loop):
        await self.auc.close()

    def on_start(self):
        """
        default function
        """
        random.shuffle(self.start_urls)
        for url in self.start_urls:
            self.crawl(url, callback=self.index_page)

    def __split_dict(self, **kwargs):
        """
        分成CrawlArg可以傳進去的參數以及不行的參數
        """
        d1 = {}
        d2 = {}
        for key, val in kwargs.items():
            d = d1 if key in CrawlArg_KEY else d2
            d[key] = val

        return d1, d2

    def __crawl_checking(self, *args, **kwargs):
        """
        在crawl or asyn_crawl之前先做前處理
        判斷是否爬過
        :return crawl_arg or None
        """
        data, other_kwargs = CrawlArg.split_dict(**kwargs)
        crawl_arg = CrawlArg(*args, **data)
        if not crawl_arg.url.startswith('http'):
            return None
        crawl_arg.other_kwargs = other_kwargs
        if self.check_crawled_urls:
            if crawl_arg.task_id is None:
                str_url = crawl_arg.url + \
                          self.__url_params_to_str(crawl_arg.params) + self.__url_params_to_str(crawl_arg.data)
                md5_url = self.get_md5(str_url)
                crawl_arg.task_id = md5_url
            if crawl_arg.task_id in self.crawled_urls:
                if self.DEBUG:
                    logger.debug("repeated url: %s %s %s", crawl_arg.url, crawl_arg.params, crawl_arg.data)
                return None
            self.crawled_urls.add(crawl_arg.task_id)

        self.__total_urls += 1
        return crawl_arg

    def crawl(self, *args, **kwargs):
        """傳遞參數是為了init CrawlArg
        如果回傳None 代表驗證爬過
        可以設定 check_crawled_urls 確認是否驗證
        > self.crawl('https://www.google.com',callback=self.parse)

        :param url(str):
        :param params(dict,default=None): url params dict
        :param data(dict,default=None): form data dict
        :param method(str,default=GET): GET or POST
        :param callback(function,default=None): callback function when get response
        :param task_id(str,default=md5 (url+params+data)): for crawled_url checking
        :param kwargs((dict 參數名字,default={}): dict for callback args
        :param rjson(bool,default=False): content is json fileFalse
        :param referer(str,default=''): for requests headers
        :param skipbotcheck(bool,default=True):
        :param allow_redirects(bool,default=False): for requests args
        :param min_content_length(int,default=self.min_content_length): response 最小長度限制
        :return:

        """
        ret = self.__crawl_checking(*args, **kwargs)
        if ret:
            self._tasks_que.put_nowait(ret)

    async def async_crawl(self, *args, **kwargs):
        """
        說明文件如 crawl
        差別在於他不是丟進去queue 而是馬上執行
        """
        ret = self.__crawl_checking(*args, **kwargs)
        if ret:
            return await self.__crawl(ret)

    def __try_fails(self):
        """
        每次只判斷第一個 fails
        如果條件到了丟進queue裡面等待執行並且將第一個pop
        """
        if not len(self.__fails):
            return
        now_time = now()
        crawl_arg = self.__fails[0]

        if self.__fails_count[crawl_arg.task_id] <= self.fail_try_num and \
                now_time - crawl_arg.now >= self.try_fail_time:
            self._tasks_que.put_nowait(crawl_arg)
            self.__fails.popleft()

    def __copy__crawl_args(self, r, crawl_arg):
        for key in CrawlArg_KEY:
            data = getattr(crawl_arg, key)
            r[key] = data.copy() if hasattr(data, 'copy') else data
        r['other_kwargs'] = getattr(crawl_arg, 'other_kwargs', {})

    async def __crawl(self, crawl_arg):
        ret = ''
        info = {}

        if crawl_arg.method == 'GET':
            ret, info = await self.auc.reachurl_more_info(
                crawl_arg.url, params=crawl_arg.params, **crawl_arg.other_kwargs)
        elif crawl_arg.method == 'POST':
            ret, info = await self.auc.posturl_more_info(
                crawl_arg.url, data=crawl_arg.data, **crawl_arg.other_kwargs)
        self.__total_crawled += 1
        try:
            info['url'] = str(info['response'].url)
        except Exception as e:
            info['url'] = None

        r = EasyDict()
        r.content = ret
        r.info = info
        # pass data to response
        self.__copy__crawl_args(r, crawl_arg)

        # to fails
        if self.auto_validate_fail and not len(ret):
            self.to_fails(r)

        if crawl_arg.callback and (not self.auto_validate_fail or len(ret)):
            if inspect.iscoroutinefunction(crawl_arg.callback):
                await crawl_arg.callback(r, **crawl_arg.kwargs)
            else:
                crawl_arg.callback(r, **crawl_arg.kwargs)

        # end
        if self.sleep_time:
            await asyncio.sleep(self.sleep_time)
        return r

    def to_fails(self, r, set_dead_proxies=False):
        """
        將response 設定fail
        example: 在amazon 如果抓不到資料 或者是需要驗證的時候 無法從response length 判斷
        可以在外部判斷沒有取得資料在丟入
        :param r: response easydict
        :param set_dead_proxies: 如果需要把proxies設定死掉的話
        :return:
        """
        self.__total_crawled -= 1
        if set_dead_proxies:
            self.auc.update_dead_proxies(proxies=r.info['proxies'])
        logger.warning('crawl fail len=%s p: %s url: %s', len(r.content), r.params, r.url)

        data, others = CrawlArg.split_dict(**r)
        crawl_args = CrawlArg(**data)
        crawl_args.now = now()
        crawl_args.other_kwargs = others.get('other_kwargs', {})
        # 更新時間
        if crawl_args in self.__fails:
            self.__fails.remove(crawl_args)
        self.__fails.append(crawl_args)
        self.__fails_count[crawl_args.task_id] += 1

    def __url_params_to_str(self, data):
        if data is None or not len(data):
            return '*'
        else:
            return str(data)

    @functools.lru_cache(maxsize=2048)
    def get_md5(self, data):
        m = hashlib.md5()
        m.update(data.encode())
        return m.hexdigest()

    def progress(self):
        """
        根據丟進queue 還有執行完的計算執行百分比 以及計算預估剩下時間
        """
        percent = round((self.__total_crawled / self.__total_urls) * 100, 2)
        spend_time = (now() - self.start_time)
        try:
            predict_time = (spend_time * 100) / percent
        except Exception as e:
            predict_time = 0
        return 'queue: %d/%d %05.2f%%|%s' % (
            self.__total_crawled,
            self.__total_urls,
            percent,
            seconds_to_time(round(predict_time))
        )

    def log_items(self, insert_count, now_page, page_count, url, other_str=None):
        str_templates = {
            self.DEBUG: """%s insert(avg|now|total): %d|%d/%d 
err/spam/esbuf/fails: %d/%d/%d/%d page: %s/%s 
url: %s""",
            not self.DEBUG: """%s insert(avg|now|total): %d|%d/%d 
err/spam: %d/%d page: %s/%s
url: %s"""
        }
        tuple_datas = {
            self.DEBUG: (self.progress(),
                         round(self.i / ((now() - self.start_time) // 60 + 1)),
                         insert_count, self.i,
                         self.error_total, self.spam_count, len(self.esbuf), len(self.__fails),
                         now_page, page_count, url),
            not self.DEBUG: (self.progress(),
                             round(self.i / ((now() - self.start_time) // 60 + 1)),
                             insert_count, self.i,
                             self.error_total, self.spam_count,
                             now_page, page_count,
                             url)
        }

        tuple_data = tuple_datas[self.DEBUG]
        str_template = str_templates[self.DEBUG]
        if other_str:
            str_template += "\n{}".format(other_str)

        logger.info(str_template, *tuple_data)

    async def workers(self):
        while True:
            try:
                crawl_arg = await self._tasks_que.get()
                self.__try_fails()
                await self.__crawl(crawl_arg)
                self._tasks_que.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception('worker')
                self._tasks_que.task_done()
            finally:
                pass
                # todo queue remove from runing_quue

    async def work(self):
        if inspect.iscoroutinefunction(self.on_start):
            await self.on_start()
        else:
            self.on_start()
        workers = [
            asyncio.Task(self.workers(), loop=self._loop)
            for _ in range(self.max_tasks)
        ]
        # 執行 on_start新增的queue
        await self._tasks_que.join()

        # 結束後 在把所有fails丟進queue
        while len(self.__fails):
            crawl_arg = self.__fails.popleft()
            self._tasks_que.put_nowait(crawl_arg)
        await self._tasks_que.join()
        # record still failed
        for i, d in enumerate(self.__fails):
            fail_log.info(d)
        for worker in workers:
            worker.cancel()

    def run(self, callback=None):
        """
        :param callback: after run done final function
        :return:
        """
        self.start_time = now()
        start_at = datetime.datetime.now()
        logger.info('time: start:%s', start_at)
        try:
            self._loop.run_until_complete(self.work())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        except asyncio.CancelledError:
            logging.warning("cancel error")
        except Exception as e:
            logger.exception('run done error: %s', str(e))
        finally:
            self.syncesbuf()

            end_at = datetime.datetime.now()
            logger.info(
                'time: %s crawl len: %s',
                seconds_to_time((end_at - start_at).total_seconds()),
                self.__total_urls
            )
            if not self.auc.bot.closed:
                if self.auc.bot._connector_owner:
                    self.auc.bot._connector.close()
                self.auc.bot._connector = None
            if callback and callable(callback):
                callback()

    async def single_work(self):
        workers = [
            asyncio.Task(self.workers(), loop=self._loop)
            for _ in range(self.max_tasks)
        ]

        await self._tasks_que.join()
        for worker in workers:
            worker.cancel()

    def run_single(self):
        """
        測試單一async func
        """
        self.max_tasks = 1
        self.start_time = now()
        start_at = datetime.datetime.now()
        logger.info('time: start:%s', start_at)
        try:
            self._loop.run_until_complete(self.single_work())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        except asyncio.CancelledError:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        finally:
            self.syncesbuf()

            end_at = datetime.datetime.now()
            logger.info(
                'time: %s crawl len: %s',
                seconds_to_time((end_at - start_at).total_seconds()),
                len(self.crawled_urls)
            )
            if not self.auc.bot.closed:
                if self.auc.bot._connector_owner:
                    self.auc.bot._connector.close()
                self.auc.bot._connector = None
