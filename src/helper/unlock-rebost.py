#!/usr/bin/python3
import sys
from rebost import store
a=store.client()
if len(sys.argv)>1:
	if sys.argv[0]!="test":
		a.lock()
else:
	a.unlock()
