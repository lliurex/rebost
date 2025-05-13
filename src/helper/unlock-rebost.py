#!/usr/bin/python3
import sys
from rebost import store
a=store.client()
if len(sys.argv)>0:
	a.lock()
else:
	a.unlock()
