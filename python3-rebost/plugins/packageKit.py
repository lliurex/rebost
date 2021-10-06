#!/usr/bin/env python3
import gi
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit
import threading
import json
import threading
import rebostHelper
import logging
import html
import os
from queue import Queue
from bs4 import BeautifulSoup

class packageKit():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self._debug("Loaded")
		self.packagekind="package"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=0
		self.progress={}
		self.queue=Queue(maxsize=0)
		self.result=''
		self.wrkDir="/tmp/.cache/rebost/xml/packageKit"
		self.pkcon=packagekit.Client()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("packagekit: %s"%str(msg))

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if not self.pkcon:
			self.pkcon=packagekit.Client()
		if action=='load':
			self._loadStore()
		return(rs)

	def getStatus(self):
		return (self.progress)

	def _loadStore(self,*args):
		action="load"
		self._debug("Getting pkg list")
		pkgList=self.pkcon.get_packages(packagekit.FilterEnum.NONE, None, self._load_callback, None)
		self._debug("End Getting pkg list")
		semaphore = threading.BoundedSemaphore(value=20)
		thList=[]
		for pkg in pkgList.get_package_array():
			if pkg.get_arch() not in ['amd64','all']:
				continue
			th=threading.Thread(target=self._th_generateRebostPkg,args=(pkg,semaphore,))
			th.start()
			thList.append(th)
		for th in thList:
			th.join()
		self._debug("PKG loaded")
		pkgList=[]
		while not self.queue.empty():
			pkgList.append(self.queue.get())
		rebostHelper.rebostPkgList_to_sqlite(pkgList,'packagekit.db')
		self._debug("SQL loaded")
	
	def _th_generateRebostPkg(self,pkg,semaphore):
		semaphore.acquire()
		if pkg.get_arch() not in ['amd64','all']:
			semaphore.release()
			return

		rebostPkg=rebostHelper.rebostPkg()
		rebostPkg['name']=pkg.get_name()
		rebostPkg['pkgname']=pkg.get_name()
		rebostPkg['id']="org.packagekit.%s"%pkg.get_name()
		rebostPkg['summary']=BeautifulSoup(pkg.get_summary(),"html.parser").get_text().replace("'","''")

		rebostPkg['name']=pkg.get_name()
		rebostPkg['summary']=html.escape(pkg.get_summary()).encode('ascii', 'xmlcharrefreplace').decode() 
		rebostPkg['description']=rebostPkg['summary']
		#rebostPkg['version']="package-{}".format(pkg.get_version())
		rebostPkg['versions']={"package":"{}".format(pkg.get_version())}
		rebostPkg['bundle']={"package":"{}".format(pkg.get_id())}
		if 'installed' in pkg.get_id():
			rebostPkg['state']={"package":"0"}
		else:
			rebostPkg['state']={"package":"1"}
		self.queue.put(rebostPkg)
		semaphore.release()

	def _load_callback(self,*args):
		return

def main():
	obj=packageKit()
	return(obj)

