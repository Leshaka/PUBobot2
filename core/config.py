# -*- coding: utf-8 -*-
from importlib.machinery import SourceFileLoader

# Load config
try:
    cfg = SourceFileLoader("cfg", "config.cfg").load_module()
except Exception as e:
    print("Failed to load config.cfg file!")
    raise e

with open(".version", "r") as f:
    __version__ = f.read()
