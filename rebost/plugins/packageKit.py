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
		self.enabled=False
		self.onlyLliurex=True
		self._debug("Loaded")
		self.packagekind="package"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=0
		self.result=''
		self.wrkDir="/tmp/.cache/rebost/xml/packageKit"
		self.lastUpdate="/usr/share/rebost/tmp/pk.lu"
		self.pkgFile="/usr/share/rebost/tmp/pk.rebost"
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="packagekit: {}".format(msg)
			rebostHelper._debug(dbg)
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
		newMd5=""
		pkgIds=self._getChanges(gPath)
		gioFile[0].delete()
		if (len(pkgIds)>0) or (pkgUpdateSack.get_size()>0):
			pkgUpdateIds={}
			pkgUpdateIdsArray=pkgUpdateSack.get_ids()
			for pkgId in pkgUpdateIdsArray:
				pkgInfo=pkgId.split(";")
				pkgUpdateIds[pkgInfo[0]]={'release':pkgInfo[1],'origin':pkgInfo[-1]}
			self._debug("End Getting pkg list")
			self._processPackages(pkcon,pkgIds,pkgUpdateIds)
			self._debug("PKG loaded")
			try:
				with open(self.lastUpdate,'w') as f:
					f.write(newMd5)
			except:
				print("Forcing update")
			self._debug("SQL loaded")
		else:
			self._debug("Skip update")
		return()
	#def _loadStore

	def _getChanges(self,gPath):
		#Compare old file with new file. Extract changes and update db
		oldPkgList=[]
		newPkgList=[]
		if os.path.isfile(self.pkgFile)==True:
			with open(self.pkgFile,'r') as f:
				oldPkgList=f.readlines()
		with open(gPath,'r') as f:
			newPkgList=f.readlines()
		pkgList= list(set(newPkgList)-set(oldPkgList))
		with open(self.pkgFile,'w') as f:
			f.writelines(newPkgList)
		pkgIds=[]
		for pkg in pkgList:
			pkgArray=pkg.split('\t')
			pkgIds.append(pkgArray[1])
		return(pkgIds)
	#def _getChanges

	def _processPackages(self,pkcon,pkgIds,pkgUpdateIds):
		pkgList=[]
		pkgDetails=[]
		pkgCount=0
		inc=5200
		total=inc
		processed=0
		pkgCount=len(pkgIds)
		self._debug("Total packages {}".format(pkgCount))
		while processed<pkgCount:
			self._debug("Processing pkg list {}".format(processed))
			(selected,updateSelected)=self._processPkgList(pkgIds[processed:total])
			####  REM WIP ON OPTIMIZATION
			# Calls to packagekit are too expensive so it's needed to replace them
			# Apparently we need a get_details call for retrieving categories
			# Perhaps it's possible to use pkg.group property but isn't working
			pkDetails=[]
			if selected:
				pkDetails=pkcon.get_details(selected, None, self._load_callback, None)
				self._debug("Sending to SQL")
				if pkDetails:
					data=self._generateRebostPkgList(pkDetails,pkgUpdateIds)
					rebostHelper.rebostPkgList_to_sqlite(data,'packagekit.db',drop=False,sanitize=False)
			if updateSelected:
				self._debug("Updating {} items".format(len(updateSelected)))
				rebostHelper.rebostPkgList_to_sqlite(updateSelected,"packagekit.db")
			else:
				self._debug("No updates detected")
			self._debug("End processing pkg list")
			processed=total
			total+=inc
			if total>pkgCount:
				total=pkgCount
			time.sleep(0.001)
	#def _processPackages

	def _processPkgList(self,pkgToProcess):
		pkgList=[]
		selected=[]
		pkgDict={}
		updateSelected=[]
		if self.onlyLliurex==True:
			lliurexPkgs=[]
			for pkg in pkgToProcess:
				if "zero-lliurex-" in pkg.lower():
					lliurexPkgs.append(pkg)
			pkgToProcess=lliurexPkgs

		#if os.path.isfile("/usr/share/rebost/packagekit.db"):
		for pkg in pkgToProcess:
			#0->Name,1->Release,2->arch,3->origin
			pkgData=pkg.split(";")
			if pkgData[2]=="i386":
				continue
			pkgName=pkg.split(";")[0]
			pkgDict[pkgName]=pkg
		#Get rows for ids
		rows=[]
		if os.path.isfile("/usr/share/rebost/packagekit.db"):
			rows=rebostHelper.get_table_pkgarray("packagekit.db",list(pkgDict.keys()))
		for row in rows:
			try:
				rowData=json.loads(row[0][1])
				rowPkg=json.loads(row[0][0])
			except:
				selected.append(item)
				continue
			del(pkgDict[rowPkg])
			#Check if there's any change on state or version
			swUpdate=False
			if ":" in itemData[3] and rowData.get('state',{}).get('package',"1")!="0":
				rowData["state"]={"package":"0"}
				swUpdate=True
			elif ":" not in itemData[3] and rowData.get('state',{}).get('package',"1")!="1":
				rowData["state"]={"package":"1"}
				swUpdate=True
			if swUpdate:
				updateSelected.append(rowData)
		#Add non existent ids
		for pkg,item in pkgDict.items():
			selected.append(item)
#		else:
#			selected=pkgToProcess
		return(selected,updateSelected)
	#def _processPkgList

	def _generateRebostPkg(self,pkg,updateInfo):
		rebostPkg=rebostHelper.rebostPkg()
		pkgId=pkg.get_package_id().split(";")
		name=pkgId[0]
		version=pkgId[1]
		origin=pkgId[-1]
		#updateVersion=updateInfo.get(name,version)
		rebostPkg['name']=name
		rebostPkg['pkgname']=rebostPkg['name']
		rebostPkg['id']="org.packagekit.{}".format(rebostPkg['name'])
		rebostPkg['summary']=pkg.get_summary()
		rebostPkg['description']=pkg.get_description()
		#Updateversion now is a list. Must be a dict with name:version!!!!
		updateVersion=updateInfo.get(name,{}).get('release',"{}".format(version))
		rebostPkg['versions']={"package":"{}".format(updateVersion)}
		#rebostPkg['versions']={"package":"{}".format(version)}
		rebostPkg['bundle']={"package":"{}".format(rebostPkg['name'])}
		#if 'installed' in pkgId:
		if ":" in origin:
			rebostPkg['state']={"package":"0"}
			rebostPkg['installed']={"package":"{}".format(version)}
		else:
			rebostPkg['state']={"package":"1"}
			rebostPkg['installed']={"package":""}
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
			rebostPkgList.append(self._generateRebostPkg(pkg,updateInfo))
		return(rebostPkgList)
	#def _th_generateRebostPkg

	def _load_callback(self,*args):
		return

def main():
	obj=packageKit()
	return(obj)

