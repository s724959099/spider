import requests
import json
import sys
import os
from pyquery import PyQuery as pq
from pprint import pprint as pp

foldr_path = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.join(foldr_path, '..')
sys.path.append(foldr_path)
sys.path.append(parent_path)
from utils import *
from proxyhandler import save_to_proxy
