from .asyncrunner import AsyncRunner


class Cralwer:
    def __init__(self):
        self.__runner = AsyncRunner(self)

    def on_start(self):
        pass
    def on_done(self):
        pass

    def run(self, callback=None):
        """
        finnaly 最後執行的function
        """
        self.__runner.run(callback)


if __name__ == '__main__':
    c = Cralwer()
    c.run()
