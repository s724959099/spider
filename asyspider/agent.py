import random
import os

def random_line(afile):
    line = next(afile)
    for num, aline in enumerate(afile):
        if random.randrange(num + 2): continue
        line = aline
    return line.strip()

def reqagent(platform='desktop'):
    platform = platform.lower()
    if platform == 'desktop':
        filename = 'agentlist_desktop.txt'
    elif platform == 'mobile':
        filename = 'agentlist_mobile.txt'
    else:
        filename = 'agentlist.txt'

    try:
        # import module with search sys.path
        with open(os.path.join(os.path.dirname(__file__), filename)) as f:
            return random_line(f)
    except:
        # import module with creating a symbolic link
        with open(os.path.join(os.path.dirname(__file__), '..', '..', filename)) as f:
            return random_line(f)
