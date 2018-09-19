import asyncio
import logging
import inspect
import traceback
import concurrent.futures
import functools
import time
import datetime

try:
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

logger = logging.getLogger(__name__)


def seconds_to_time(s):
    s = int(s)
    m = s // 60
    h = m // 60
    m = m - h * 60
    s = s - m * 60 - h * 60 * 60
    return "%02d:%02d:%02d" % (h, m, s)


class AsyncRunner:
    __loop = asyncio.get_event_loop()
    __tasks_que = asyncio.Queue(loop=__loop)

    def __init__(self, crawler):
        self.crawler = crawler

    async def execute(self):
        """
        run execute method
        """
        workers = [
            asyncio.Task(self.workers(), loop=self.__loop)
            for _ in range(self.crawler.max_tasks)
        ]
        self.crawler.add_task(callback=self.crawler.on_start)
        # 執行 on_start新增的queue
        await self.__tasks_que.join()

        # 結束後 在把所有fails丟進queue
        self.crawler.first_try_fails()
        await self.__tasks_que.join()
        self.crawler.still_fails_process()
        for worker in workers:
            worker.cancel()

    def add_task(self, task):
        self.__tasks_que.put_nowait(task)

    async def workers(self):
        while True:
            try:
                crawl_arg = await self.__tasks_que.get()
                await self.crawler.work(crawl_arg)
                self.__tasks_que.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception('runner error:')
                self.__tasks_que.task_done()
            finally:
                # todo queue remove from runing_quue
                pass

    def run(self, callback=None):
        """
        :param callback: after run done final function
        :return:
        """
        # todo 開始時間
        start_at = datetime.datetime.now()
        logger.info('time: start:%s', start_at)
        try:
            self.__loop.run_until_complete(self.execute())
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        except asyncio.CancelledError:
            logger.warning("cancel error")
        except Exception as e:
            logger.exception('run done error: %s', str(e))
        finally:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            self.crawler.on_done()
            end_at = datetime.datetime.now()
            logger.info(
                'finish time: %s',
                seconds_to_time((end_at - start_at).total_seconds()),
            )
            if callback and callable(callback):
                callback()

    async def async_method(self, method, *args, **kwargs):
        ioloop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        return await ioloop.run_in_executor(executor, functools.partial(method, url, **bot_args))
