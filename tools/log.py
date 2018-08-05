import logging
import logging.handlers
import os
import datetime
import logging.config
import uuid
import sys

# import 這個才會有顏色
try:
    import curses
except ImportError:
    curses = None

logdir = os.path.join(os.path.dirname(__file__), '../logs')
uid = str(uuid.uuid4())[0:4]
now_str = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
logger = logging.getLogger()


def _stderr_supports_color():
    if os.getenv('LOGZERO_FORCE_COLOR') == '1':
        return True
    if os.name == 'nt':
        return True
    if curses and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                return True
        except Exception:
            pass
    return False


def to_unicode(value):
    """
    Converts a string argument to a unicode string.
    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, str):
        return value
    if not isinstance(value, bytes):
        raise TypeError(
            "Expected bytes, unicode, or None; got %r" % type(value))
    return value.decode("utf-8")


def _safe_unicode(s):
    try:
        return to_unicode(s)
    except UnicodeDecodeError:
        return repr(s)


def code_to_chars(code):
    CSI = '\033['
    return CSI + str(code) + 'm'


class AnsiFore:
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 39

    def __init__(self):
        for name in dir(self):
            if not name.startswith('_'):
                value = getattr(self, name)
                setattr(self, name, code_to_chars(value))


ForegroundColors = AnsiFore()


class LogFormatter(logging.Formatter):
    DEFAULT_FORMAT = _fmt = '%(color)s[%(levelname)s {} %(process)d %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s'.format(
        uid)
    DEFAULT_DATE_FORMAT = '%y%m%d %H:%M:%S'
    DEFAULT_COLORS = {
        logging.DEBUG: ForegroundColors.CYAN,
        logging.INFO: ForegroundColors.GREEN,
        logging.WARNING: ForegroundColors.YELLOW,
        logging.ERROR: ForegroundColors.RED
    }

    def __init__(self,
                 color=True,
                 fmt=DEFAULT_FORMAT,
                 datefmt=DEFAULT_DATE_FORMAT,
                 colors=DEFAULT_COLORS):
        logging.Formatter.__init__(self, datefmt=datefmt)

        self._fmt = fmt
        self._colors = {}
        self._normal = ''

        if color and _stderr_supports_color():
            self._colors = colors
            self._normal = ForegroundColors.RESET

    def format(self, record):
        try:
            message = record.getMessage()
            assert isinstance(message, str)
            record.message = message
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)

        record.asctime = self.formatTime(record, self.datefmt)

        if record.levelno in self._colors:
            record.color = self._colors[record.levelno]
            record.end_color = self._normal
        else:
            record.color = record.end_color = ''

        formatted = self._fmt % record.__dict__

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            lines = [formatted.rstrip()]
            lines.extend(
                _safe_unicode(ln) for ln in record.exc_text.split('\n'))
            formatted = '\n'.join(lines)
        return formatted.replace("\n", "\n    ")


class MonoLogFormatter(LogFormatter):
    def __init__(self, *args, **kwargs):
        kwargs['color'] = False
        super().__init__(*args, **kwargs)


def gen_file(name, debug=False):
    if debug:
        file_name = "{}.log".format(name)
        file_name = os.path.join(logdir, file_name)
    else:
        file_name = "{}_{}_{}.log".format(name, now_str, uid)
        file_name = os.path.join(logdir, file_name)
    return file_name


def get_status_file(name):
    es_logdir = os.path.join(os.environ['HOME'], 'var/crawler_status')
    if not os.path.exists(es_logdir):
        os.mkdir(es_logdir)
    file_name = "{}_{}.log".format(name, now_str[:8])
    file_name = os.path.join(es_logdir, file_name)
    return file_name


def dict_merge(dct, merge_dct):
    for k, v in merge_dct.items():
        if k in dct and isinstance(dct[k], dict):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


def dictConfig(config=None, name=None, level=logging.INFO, debug=False,
               loggers=None, maxBytes=10e9, backupCount=1, **kwargs):
    """
    debug
        如果不是debug 每次執行都會產生一個log file
    debug and loggers=None
        預設會產生 ['eslib2', 'abike_fails', 'abike'] 三個loger 到logfile
    config
        更新預設的dict
    name
        file name
    level
        預設所有loggers都是相同level
    maxBytes and backupCount
        預設在debug 才有
        否則每次執行都會產生一個新的file 也就不需要了
    kwargs
        disable_existing_loggers
            True 取消其他之前init的loggers

    """
    if not debug:
        maxBytes = 0
        backupCount = 0

    if config is None:
        config = {}
    disable_existing_loggers = kwargs.get('disable_existing_loggers', False)
    level_dict = {}
    for key in dir(logging):
        val = getattr(logging, key)
        if isinstance(key, str) and key.lower() in "debug warning warn info error".split():
            if not callable(val):
                level_dict[val] = key
    level_str = level_dict.get(level, 'INFO')
    if loggers is None:
        loggers = []

    if debug or len(loggers) == 0:
        loggers = ['eslib2', 'abike_fails', 'abike', 'request_mixin', 'debug', '']

    file_name = gen_file(name, debug) if name else None
    base_config = {
        'version': 1,
        'disable_existing_loggers': disable_existing_loggers,
        'formatters': {
            'standard': {
                '()': LogFormatter
            },
            'mono_color': {
                '()': MonoLogFormatter
            },
            'crawler_status': {
                'format': '%(message)s'
            }
        },
        'handlers': {
            'stream_handler': {
                'level': level_str,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
            'crawler_status_handler': {
                'filename': get_status_file(name),
                'level': logging.DEBUG,
                'formatter': 'crawler_status',
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 0,
                'backupCount': 0,
                "encoding": "utf8"
            }
        },
        'loggers': {
            '': {
                # 沒有name的不儲存
                'handlers': [],
                'level': level_str,
                'propagate': True
            },
            'requests': {
                'level': logging.WARNING,
                'propagate': True
            },
            'elasticsearch': {
                'level': logging.WARNING,
                'propagate': True
            },
            'crawler_status': {
                'handlers': ['crawler_status_handler'],
                'level': logging.INFO,
                'propagate': False
            },
        }
    }
    if file_name:
        base_config['handlers']['rotate_file_handler'] = {
            'filename': file_name,
            'level': level_str,
            'formatter': 'mono_color',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 10e9,
            'backupCount': 1,
            "encoding": "utf8"
        }

    # add other logger to same file
    for lgr_key in loggers:
        base_config['loggers'][lgr_key] = {
            'handlers': ['stream_handler', 'rotate_file_handler'] if name else ['stream_handler'],
            'level': level_str,
            'propagate': False
        }
    real_config = base_config.copy()
    # 可以單獨寫loggers 而不會覆蓋舊有的
    dict_merge(real_config, config)
    logging.config.dictConfig(real_config)


def setup_logger(*args, **kwargs):
    pass


def initlog(logfile=None, logdir=None, level=logging.INFO,
            maxBytes=10e9, backupCount=1, debug=False,
            **kwargs
            ):
    """
    參考dictConfig config={...} 可以更改default init方式
    """
    if not logdir:
        logdir = logdir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    dictConfig(name=logfile, level=level, debug=debug,
               maxBytes=maxBytes, backupCount=backupCount, **kwargs)


def getLogger(ec_type=None, provide=None, name=None):
    dirname = os.path.dirname(__file__)
    logger_name = '.'.join(filter(None, [ec_type, provide, name]))
    return logging.getLogger(logger_name)


def save_sample(name, data, mode='w'):
    logdir = os.path.join(os.environ['HOME'], 'var/log')
    try:
        os.makedirs(logdir)
    except Exception as e:
        pass

    filename = os.path.join(logdir, name + '.%s' % datetime.datetime.now().strftime('%Y%m%d.%H%M%S'))
    with open(filename, mode) as fd:
        fd.write(data)
    return filename


if __name__ == '__main__':
    """
    output:
    level uid date time module_name file_line msg
    [I ee39 180621 08:09:12 log:129] INFO
    [D ee39 180621 08:09:12 log:130] DEBUG
    [I ee39 180621 08:09:12 log:132] sub info
    [D ee39 180621 08:09:12 log:133] sub debug
    """
    initlog('kk', level=logging.INFO, config=dict(
        loggers={
            'test': {
                'level': logging.WARNING,
                'propagate': True
            },
        }
    ))
    logger = logging.getLogger()
    logger.info('test demo')
    lgr = getLogger('test')
    lgr.info('test sub')
