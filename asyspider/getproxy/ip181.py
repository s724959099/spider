from config import *

url = 'http://www.ip181.com/'
r = requests.get(url)
data = json.loads(r.content.decode())
result = []
for el in data.get('RESULT'):
    result.append(dict(
        source='ip181',
        country=el.get('position'),
        ip=el.get('ip'),
        port=el.get('port')
    ))

save_to_proxy(result)
pp(result)
print('total:', len(result))
