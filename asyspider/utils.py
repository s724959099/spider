import os
import json

dir_path = os.path.dirname(os.path.realpath(__file__))


def save_json(name, data):
    file_name = os.path.join(dir_path, './datas/{}'.format(name))

    with open(file_name, 'w') as f:
        json.dump(data, f)


def read_json(name):
    file_name = os.path.join(dir_path, './datas/{}'.format(name))
    ret = None
    with open(file_name, 'r') as f:
        ret = json.loads(f.read())
    return ret


if __name__ == '__main__':
    d = [dict(a=3)]
    # save_json('demo.json', d)
    r = read_json('demo.json')
    print(r)
