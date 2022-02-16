#!/usr/bin/env python3
import gi
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit
import threading
import json
import rebostHelper
import logging
import html
import os
from queue import Queue
from bs4 import BeautifulSoup
import hashlib
import time

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
		self.result=''
		self.wrkDir="/tmp/.cache/rebost/xml/packageKit"
		self.lastUpdate="/usr/share/rebost/tmp/pk.lu"
		self.aptCache="/var/cache/apt/pkgcache.bin"

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
		if action=='load':
			self._loadStore()
		return(rs)

	def getStatus(self):
		return (self.progress)

	def _loadStore(self,*args):
		action="load"
		update=self._chkNeedUpdate()
		if update:
			self._debug("Getting pkg list")
			pkcon=packagekit.Client()
			pkgList=pkcon.get_packages(packagekit.FilterEnum.NONE, None, self._load_callback, None)
			self._debug("End Getting pkg list")
			pkgArray=pkgList.get_package_array()
			pkgCount=len(pkgArray)
			inc=5200
			total=inc
			processed=0
			self._debug("Total packages {}".format(pkgCount))
			rebostHelper.rebostPkgList_to_sqlite([],'packagekit.db',drop=True)
			while processed<pkgCount:
				pkgList=[]
				self._debug("Processing pkg list {}".format(processed))
				pkgIdArray=[]
				selected=pkgArray[processed:total]
				while selected:
					pkg=selected.pop(0)
					if (pkg.get_arch()=='amd64' or pkg.get_arch()=='all')==False:
						continue
					pkgIdArray.append(pkg.get_id())
				if pkgIdArray:
					pkcon=packagekit.Client()
					pkDetails=pkcon.get_details(pkgIdArray, None, self._load_callback, None)
					pkgDetails=pkDetails.get_details_array()
					rebostHelper.rebostPkgList_to_sqlite(self._generateRebostPkg(pkgDetails),'packagekit.db',drop=False)
				self._debug("End processing pkg list")
				processed=total
				total+=inc
				if total>pkgCount:
					total=pkgCount
				time.sleep(0.09)
			self._debug("PKG loaded")
			with open(self.aptCache,'rb') as f:
				faptContent=f.read()
			aptMd5=hashlib.md5(faptContent).hexdigest()
			with open(self.lastUpdate,'w') as f:
				f.write(aptMd5)
			self._debug("SQL loaded")
		else:
			self._debug("Skip update")
		return()
	#def _loadStore

	def _chkNeedUpdate(self):
		update=True
		aptMd5=""
		lastUpdate=""
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
		else:
			fcontent=""
			with open(self.lastUpdate,'r') as f:
				lastUpdate=f.read()
			with open(self.aptCache,'rb') as f:
				faptContent=f.read()
			aptMd5=hashlib.md5(faptContent).hexdigest()
			if aptMd5==lastUpdate:
				update=False
		return(update)
	#def _chkNeedUpdate

	def _generateRebostPkg(self,pkgList):
		rebostPkgList=[]
		#for pkg in pkgList:
		while pkgList:
			pkg=pkgList.pop(0)
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
			if ("lliurex" in rebostPkg['name'].lower() or ("lliurex" in rebostPkg['homepage'].lower())):
				rebostPkg['categories'].insert(0,'Lliurex')
			rebostPkgList.append(rebostPkg)
		return(rebostPkgList)
	#def _th_generateRebostPkg

	def _load_callback(self,*args):
		return

def main():
	obj=packageKit()
	return(obj)

