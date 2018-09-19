import sys
import pathlib
import os
import subprocess
import threading

path_str = os.path.dirname(os.path.realpath(__file__))
folder_path = pathlib.Path(path_str)
execute_files = list(map(lambda x: [sys.executable, str(x)], folder_path.glob('getproxy/*.py')))
print('len: %s' % (len(execute_files)))
threads = []
for i in range(len(execute_files)):
    el = execute_files[i]
    threads.append(threading.Thread(target=subprocess.call, args=(el,)))
    threads[i].start()

for i in range(len(execute_files)):
    threads[i].join()
