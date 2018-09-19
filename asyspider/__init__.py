from .crawler import Crawler
from .fetcher import headers_raw_to_dict
from .proxyhandler import save_to_proxy, ProxyHandler

__all__ = list(
    map(lambda x: x.__name__,
        [Crawler, headers_raw_to_dict, ProxyHandler]))
