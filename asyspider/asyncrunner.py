import asyncio
import logging
import inspect

logger = logging.getLogger(__name__)


class AsyncRunner:
    __loop = asyncio.get_event_loop()
    __tasks_que = asyncio.Queue(loop=__loop)

    def __init__(self, crawler):
        self.crawler = crawler

    async def execute(self):
        await self.crawler.on_start() \
            if inspect.iscoroutinefunction(self.crawler.on_start) \
            else self.crawler.on_start()
        workers = [
            asyncio.Task(self.workers(), loop=self.__loop)
            for _ in range(self.crawler.max_tasks)
        ]
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
                pass
                # todo queue remove from runing_quue

    def run(self, callback=None):
        """
        :param callback: after run done final function
        :return:
        """
        # todo 開始時間
        # self.start_time = now()
        # start_at = datetime.datetime.now()
        # logger.info('time: start:%s', start_at)
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
            self.crawler.on_done()
            # todo 結束時間
            # end_at = datetime.datetime.now()
            # logger.info(
            #     'time: %s crawl len: %s',
            #     seconds_to_time((end_at - start_at).total_seconds()),
            #     self.__total_urls
            # )
            # todo bot close
            # if not self.auc.bot.closed:
            #     if self.auc.bot._connector_owner:
            #         self.auc.bot._connector.close()
            #     self.auc.bot._connector = None
            if callback and callable(callback):
                callback()
