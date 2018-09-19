from config import *

url = 'https://free-proxy-list.net/'
r = requests.get(url)
dom = pq(r.content.decode())
result = []

for _el in dom('#proxylisttable > tbody > tr').items():
    el = lambda x: _el('td:eq({})'.format(x)).text()
    result.append(dict(
        source='freeproxy',
        country=el(3),
        ip=el(0),
        port=el(1),
        https=el(6),
        anonymity=el(4)
    ))

save_to_proxy(result)
pp(result)
print('total:', len(result))
