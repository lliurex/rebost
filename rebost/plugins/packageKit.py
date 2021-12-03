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
		self.dbg=False
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
		semaphore = threading.BoundedSemaphore(value=20)
		thList=[]
		pkgIdArray=[]
		pkgArray=pkgList.get_package_array()
		for pkg in pkgArray:
			if pkg.get_arch() not in ['amd64','all']:
				continue
			pkgIdArray.append(pkg.get_id())
		pkgCount=len(pkgIdArray)
		total=5000
		processed=0
		while processed<pkgCount:
			pkgDetails=self.pkcon.get_details(pkgIdArray[processed:total], None, self._load_callback, None)
			for pkg in pkgDetails.get_details_array():
				th=threading.Thread(target=self._th_generateRebostPkg,args=(pkg,semaphore,))
				th.start()
				thList.append(th)
			for th in thList:
				th.join()
			processed=total
			total+=4000
			if total>pkgCount:
				total=pkgCount
		self._debug("End Getting pkg list")
		pkgList=[]
		while not self.queue.empty():
			pkgList.append(self.queue.get())
		self._debug("PKG loaded")
		rebostHelper.rebostPkgList_to_sqlite(pkgList,'packagekit.db')
		self._debug("SQL loaded")
	
	def _getCategories(self,pkg):
		#Categories in apt are not full freedesktop standar
		pkgProperties=self.pkcon.get_details((pkg['bundle']['package'],),None,self._load_callback,None)
		for prop in pkgProperties.get_details_array():
			pkgCategory=prop.get_group()
			pkg['categories'].append(pkgCategory.to_string(pkgCategory))
			break
		return(pkg)

	def _th_generateRebostPkg(self,pkg,semaphore):
		semaphore.acquire()
		rebostPkg=rebostHelper.rebostPkg()
		pkgId=pkg.get_package_id()
		rebostPkg['name']=pkgId.split(";")[0]
		rebostPkg['pkgname']=rebostPkg['name']
		rebostPkg['id']="org.packagekit.{}".format(rebostPkg['name'])
		rebostPkg['summary']=pkg.get_summary()
		rebostPkg['description']=pkg.get_description()
		#rebostPkg['version']="package-{}".format(pkg.get_version())
		rebostPkg['versions']={"package":"{}".format(pkgId.split(";")[1])}
		rebostPkg['bundle']={"package":"{}".format(rebostPkg['name'])}
		if 'installed' in pkgId:
			rebostPkg['state']={"package":"0"}
		else:
			rebostPkg['state']={"package":"1"}
		rebostPkg['size']={"package":"{}".format(pkg.get_size())}
		rebostPkg['homepage']=pkg.get_url()
		rebostPkg['license']=pkg.get_license()
		rebostPkg['categories'].append(pkg.get_group().to_string(pkg.get_group()).lower())
		if ("zero-lliurex" in rebostPkg['name'].lower() or ("lliurex" in rebostPkg['homepage'].lower())):
			rebostPkg['categories'].append("Lliurex")
		self.queue.put(rebostPkg)
		semaphore.release()
	#def _th_generateRebostPkg

	def _load_callback(self,*args):
		return

def main():
	obj=packageKit()
	return(obj)

