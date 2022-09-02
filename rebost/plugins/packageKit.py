#!/usr/bin/env python3
import gi
from gi.repository import Gio
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
		self.result=''
		self.wrkDir="/tmp/.cache/rebost/xml/packageKit"
		self.lastUpdate="/usr/share/rebost/tmp/pk.lu"
	#def __init__

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			logging.warning("packagekit: %s"%str(msg))
	#def _debug

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)
	#def execute

	def _loadStore(self,*args):
		action="load"
		self._debug("Getting pkg list")
		pkcon=packagekit.Client()
		pkList=pkcon.get_packages(packagekit.FilterEnum.NONE, None, self._load_callback, None)
		pkgSack=pkList.get_package_sack()
		#Needed for controlling updates
		gioFile=Gio.file_new_tmp()
		pkgSack.to_file(gioFile[0])
		gPath=gioFile[0].get_path()
		pkUpdates=pkcon.get_updates(packagekit.FilterEnum.NONE, None, self._load_callback, None)
		pkgUpdateSack=pkUpdates.get_package_sack()
		updateFile=Gio.file_new_tmp()
		pkgUpdateSack.to_file(updateFile[0])
		updatePath=updateFile[0].get_path()
		newMd5=self._getNewMd5(gPath,updatePath)
		gioFile[0].delete()
		updateFile[0].delete()
		pkgUpdateIdsArray=pkgUpdateSack.get_ids()
		if newMd5!='':
			pkgUpdateIds={}
			for ids in pkgUpdateIdsArray:
				name=ids.split(";")[0]
				pkgUpdateIds[name]=ids.split(";")[1]
			pkgList=[]
			pkgDetails=[]
			self._debug("End Getting pkg list")
			pkgCount=0
			inc=5200
			total=inc
			processed=0
			self._debug("Total packages {}".format(pkgCount))
			rebostHelper.rebostPkgList_to_sqlite([],'packagekit.db',drop=True)
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
				self._debug("End processing pkg list")
				processed=total
				total+=inc
				if total>pkgCount:
					total=pkgCount
				self._debug("Sending to SQL")
				rebostHelper.rebostPkgList_to_sqlite(self._generateRebostPkgList(pkDetails,pkgUpdateIds),'packagekit.db',drop=False,sanitize=False)
				time.sleep(0.001)
			self._debug("PKG loaded")
			try:
				with open(self.lastUpdate,'w') as f:
					f.write(newMd5)
			except:
				print("chkNeedUpdate disabled")
			self._debug("SQL loaded")
		else:
			self._debug("Skip update")
		return()
	#def _loadStore

	def _getNewMd5(self,gPath,updatePath=''):
		gioMd5=''
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
		else:
			updateContent=''
			lastUpdate=""
			with open(self.lastUpdate,'r') as f:
				lastUpdate=f.read()
			with open(gPath,'rb') as f:
				gioContent=f.read()
			if os.path.isfile(updatePath):
				with open(updatePath,'rb') as f:
					updateContent=f.read()
			gioMd5=hashlib.md5(gioContent+updateContent).hexdigest()
			if gioMd5==lastUpdate:
				gioMd5=""
		return(gioMd5)
	#def _getNewMd5

	def _generateRebostPkg(self,pkg,updateInfo):
		rebostPkg=rebostHelper.rebostPkg()
		pkgId=pkg.get_package_id()
		name=pkgId.split(";")[0]
		version=pkgId.split(";")[1]
		updateVersion=updateInfo.get(name,version)
		rebostPkg['name']=name
		rebostPkg['pkgname']=rebostPkg['name']
		rebostPkg['id']="org.packagekit.{}".format(rebostPkg['name'])
		rebostPkg['summary']=pkg.get_summary()
		rebostPkg['description']=pkg.get_description()
		rebostPkg['versions']={"package":"{}".format(updateVersion)}
		rebostPkg['bundle']={"package":"{}".format(rebostPkg['name'])}
		if 'installed' in pkgId:
			rebostPkg['state']={"package":"0"}
			rebostPkg['installed']={"package":"{}".format(version)}
		else:
			rebostPkg['state']={"package":"1"}
		rebostPkg['size']={"package":"{}".format(pkg.get_size())}
		rebostPkg['homepage']=pkg.get_url()
		rebostPkg['license']=pkg.get_license()
		rebostPkg['categories'].append(pkg.get_group().to_string(pkg.get_group()).lower())
		if ("lliurex" in rebostPkg['name'].lower() or ("lliurex" in rebostPkg['homepage'].lower())):
			rebostPkg['categories'].insert(0,'Lliurex')
			rebostPkg['categories'].extend(["",""])
		if os.path.isfile(os.path.join("/usr/share/rebost-data/icons/64x64/","{0}_{0}.png".format(rebostPkg['name']))):
			rebostPkg['icon']=os.path.join("/usr/share/rebost-data/icons/64x64/","{0}_{0}.png".format(rebostPkg['name']))
		elif os.path.isfile(os.path.join("/usr/share/rebost-data/icons/128x128/","{0}_{0}.png".format(rebostPkg['name']))):
			rebostPkg['icon']=os.path.join("/usr/share/rebost-data/icons/128x128/","{0}_{0}.png".format(rebostPkg['name']))
		return(rebostPkg)
	#def _th_generateRebostPkg

	def _generateRebostPkgList(self,pkgList,updateInfo):
		rebostPkgList=[]
		for pkg in pkgList.get_details_array():
			rebostPkg=rebostHelper.rebostPkg()
			pkgId=pkg.get_package_id()
			name=pkgId.split(";")[0]
			version=pkgId.split(";")[1]
			updateVersion=updateInfo.get(name,version)
			rebostPkg['name']=name
			rebostPkg['pkgname']=rebostPkg['name']
			rebostPkg['id']="org.packagekit.{}".format(rebostPkg['name'])
			rebostPkg['summary']=pkg.get_summary()
			rebostPkg['description']=pkg.get_description()
			rebostPkg['versions']={"package":"{}".format(updateVersion)}
			rebostPkg['bundle']={"package":"{}".format(rebostPkg['name'])}
			if 'installed' in pkgId:
				rebostPkg['state']={"package":"0"}
				rebostPkg['installed']={"package":"{}".format(version)}
			else:
				rebostPkg['state']={"package":"1"}
			rebostPkg['size']={"package":"{}".format(pkg.get_size())}
			rebostPkg['homepage']=pkg.get_url()
			if not isinstance(rebostPkg['homepage'],str):
				rebostPkg['homepage']=''

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

