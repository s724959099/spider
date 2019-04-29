import json
from pprint import pprint as pp
import re

with open('./data.json', 'r') as f:
    data = json.loads(f.read())

ret = filter(lambda x: x['recomand'] > 400, data)
ret = list(ret)
pp(sorted(ret, key=lambda x: x['recomand'], reverse=True))
# %%
target = "異|掛|世|界|遊"
ret = []
for el in data:
    if re.findall(target, el['title']) or re.findall(target, el['desc']):
        ret.append(el)

print()
