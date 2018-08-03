import asyncio


class AsyncRunner:
    __loop = asyncio.get_event_loop()

    def __init__(self, crawler):
        self.cralwer = cralwer

    async def execute(self):
        pass

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
            logging.warning("cancel error")
        except Exception as e:
            logger.exception('run done error: %s', str(e))
        finally:
            self.cralwer.on_done()
            # todo 結束時間
            # end_at = datetime.datetime.now()
            # logger.info(
            #     'time: %s crawl len: %s',
            #     seconds_to_time((end_at - start_at).total_seconds()),
            #     self.__total_urls
            # )
            if not self.auc.bot.closed:
                if self.auc.bot._connector_owner:
                    self.auc.bot._connector.close()
                self.auc.bot._connector = None
            if callback and callable(callback):
                callback()
