#!/Users/Admin/anaconda3/envs/py36-anaconda/bin/python
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from crawler import *
from clint.textui import puts, indent, colored
import manager as mg

log.initlog('DEMO', level=logging.DEBUG, debug=True)

with open(os.path.join(os.path.dirname(__file__), 'keyword.txt'), 'r', encoding="utf-8") as f:
    keywords = f.read().split('\n')
pattern = "|".join(keywords)


def print_article(include=True, articles=None):
    def wrapper():
        pt_count = 0
        import collections
        ddct = collections.defaultdict(list)

        def condi(el):
            if include:
                return any([
                    re.findall(pattern, el['title'].lower()),
                    re.findall(pattern, el['content'].lower())
                ])
            else:
                return not any([
                    re.findall(pattern, el['title'].lower()),
                    re.findall(pattern, el['content'].lower())
                ])

        total = 0
        for idx, el in enumerate(articles):
            if condi(el):
                ddct[el['category']].append(el)
                total += 1
        for key in ddct:
            pt_count = 0
            idx = 0
            for el in ddct[key]:
                total -= 1
                idx += 1
                print('{} {}|| {} url: {}'.format(idx, el['category'], el['title'], el['url']))
                pt_count += 1
                if pt_count >= 10 and len(ddct[key]) - idx:
                    input('> 請輸入Enter按鍵 {}-{}<'.format(len(ddct[key]) - idx, total))
                    pt_count = 0
            input('> 請輸入Enter按鍵 {}<'.format(total))

    return wrapper


def input_check_int(text):
    while True:
        choice = input(text)
        try:
            choice = int(choice)
            return choice
        except Exception as e:
            continue


def yes_or_no(text):
    dmap = dict(
        y=True, Y=True,
        n=False, N=False
    )
    while True:
        choice = input(text)
        if choice not in dmap:
            continue
        break
    return dmap[choice]


def run_crawler():
    c = Crawler()
    c.run()


def delete_all_db():
    choice = yes_or_no('你確定嗎?[y/n]')
    if choice:
        file = os.path.join(os.path.dirname(__file__), './db.json')
        os.remove(file)
        table()
    else:
        delete_table()


def delete_table_category():
    def delete_then_again(category):
        def wrapper():
            mg.remove_articles_by_categories(category)
            delete_table_category()

        return wrapper

    index = 0
    dct_choice = dict()
    dct = mg.get_categories_info()
    for category, counts in dct.items():
        index += 1
        dct_choice[index] = category
        puts(colored.blue('{}. {} ->{}'.format(index, category, counts)))
    puts(colored.yellow('任何時候輸入 0 回到根目錄'))
    choice = input_check_int('請輸入選項: ')
    execute = dict()
    for key in dct_choice:
        execute[key] = delete_then_again(dct_choice[key])
    execute[0] = table
    execute[choice]()


def delete_table():
    puts(colored.blue('1. 刪除所有資料'))
    puts(colored.blue('2. 根據類別刪除'))
    puts(colored.yellow('任何時候輸入 0 回到根目錄'))
    choice = input_check_int('請輸入選項: ')
    execute = dict()
    execute[1] = delete_all_db
    execute[2] = delete_table_category
    execute[0] = table
    execute[choice]()


def table():
    puts(colored.blue('1. 抓取所有資料'))
    puts(colored.blue('2. 閱讀資料'))
    puts(colored.blue('3. 刪除資料'))
    puts(colored.yellow('任何時候輸入 0 回到根目錄'))
    choice = input_check_int('請輸入選項: ')
    execute = dict()
    execute[1] = run_crawler
    execute[2] = read_table
    execute[3] = delete_table
    execute[0] = table
    execute[choice]()


def read_table_all():
    puts(colored.blue('1. 包含關鍵字'))
    puts(colored.blue('2. 不包含關鍵字'))
    puts(colored.yellow('任何時候輸入 0 回到根目錄'))
    choice = input_check_int('請輸入選項: ')
    execute = dict()
    articles = mg.get_articles()
    execute[1] = print_article(include=True, articles=articles)
    execute[2] = print_article(include=False, articles=articles)
    execute[0] = table
    execute[choice]()


def read_table():
    puts(colored.blue('1. 所有文章'))
    puts(colored.blue('2. 根據類別'))
    puts(colored.yellow('任何時候輸入 0 回到根目錄'))
    choice = input_check_int('請輸入選項: ')
    execute = dict()
    execute[1] = read_table_all
    execute[2] = read_table_chose
    execute[0] = table
    execute[choice]()
    read_table()


def read_table_by_category(category):
    def wrapper():
        def myfn(include, articles):
            def _wrap():
                print_article(include=include, articles=articles)()
                read_table_by_category(category)()

            return _wrap

        def delete_then_again(category):
            def wrapper():
                mg.remove_articles_by_categories(category)
                read_table_chose()

            return wrapper

        puts(colored.red(category))
        puts(colored.blue('1. 包含關鍵字'))
        puts(colored.blue('2. 不包含關鍵字'))
        puts(colored.blue('3. 上一頁'))
        puts(colored.blue('4. 刪除該類別'))
        puts(colored.yellow('任何時候輸入 0 回到根目錄'))
        choice = input_check_int('請輸入選項: ')
        execute = dict()
        articles = mg.get_articles_by_categories(category)
        execute[1] = myfn(True, articles)
        execute[2] = myfn(False, articles)
        execute[3] = read_table_chose
        execute[4] = delete_then_again(category)
        execute[0] = table
        execute[choice]()

    return wrapper


def read_table_chose():
    index = 0
    dct_choice = dict()
    dct = mg.get_categories_info()
    for category, counts in dct.items():
        index += 1
        dct_choice[index] = category
        puts(colored.blue('{}. {} ->{}'.format(index, category, counts)))
    puts(colored.yellow('任何時候輸入 0 回到根目錄'))
    choice = input_check_int('請輸入選項: ')
    execute = dict()
    for key in dct_choice:
        execute[key] = read_table_by_category(dct_choice[key])
    execute[0] = table
    execute[choice]()


if __name__ == '__main__':
    with indent(4, quote=' >'):
        table()
