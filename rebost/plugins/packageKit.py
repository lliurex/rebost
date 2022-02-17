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
			pkList=pkcon.get_packages(packagekit.FilterEnum.NONE, None, self._load_callback, None)
			pkgList=[]
			pkgDetails=[]
			self._debug("End Getting pkg list")
			#pkgArray=pkgList.get_package_array()
			pkgCount=0#len(pkList)
			inc=5200
			total=inc
			processed=0
			self._debug("Total packages {}".format(pkgCount))
			rebostHelper.rebostPkgList_to_sqlite([],'packagekit.db',drop=True)
			pkgSack=pkList.get_package_sack()
			pkgIds=pkgSack.get_ids()
			pkgCount=len(pkgIds)
			while processed<pkgCount:
				pkgList=[]
				self._debug("Processing pkg list {}".format(processed))
				pkgIdArray=[]
				selected=pkgIds[processed:total]
				####  REM WIP ON OPTIMIZATION
				# Calls to packagekit are too expensive so it's needed to replace them
				# Apparently we need a get_details call for retrieving categories
				# Perhaps it's possible to use pkg.group property but isn't working
				pkDetails=pkcon.get_details(selected, None, self._load_callback, None)
				#pkgList.extend(self._generateRebostPkgList(pkDetails))
				self._debug("End processing pkg list")
				processed=total
				total+=inc
				if total>pkgCount:
					total=pkgCount
				self._debug("Sending to SQL")
				rebostHelper.rebostPkgList_to_sqlite(self._generateRebostPkgList(pkDetails),'packagekit.db',drop=False,sanitize=False)
				time.sleep(0.001)

		####for pkg in pkgSack:
		####	pkgDetails.append(pkg.get_id())
		####	if len(pkgDetails)>=inc:
		####		pkDetails=pkcon.get_details(pkgDetails, None, self._load_callback, None)
		####	#pkgDetails=pkDetails.get_details_array()
		####		#for pkgD in pkDetails.get_details_array():
		####		#	print(".")
		####		pkgList.extend(pkDetails.get_details_array())
		####		pkDetails=[]
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

	def _generateRebostPkg(self,pkg):
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
			rebostPkg['categories'].extend(["",""])
		return(rebostPkg)
	#def _th_generateRebostPkg
	def _generateRebostPkgList(self,pkgList):
		rebostPkgList=[]
		#for pkg in pkgList:
		#while pkgList:
		for pkg in pkgList.get_details_array():
			#pkg=pkgList.pop(0)
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

