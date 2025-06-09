#!/usr/bin/env python3
import gi,shutil,stat
from gi.repository import Gio
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit
import json
import rebostHelper
import libAppsEdu
import logging
import os
import time

class packageKit():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.onlyLliurex=False
		self._debug("Loaded")
		self.packagekind="package"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=2
		self.result=''
		self.restricted=True
		dbCache="/tmp/.cache/rebost"
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER"))
		if os.path.exists(self.rebostCache)==False:
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.wrkDir=os.path.join(self.rebostCache,"xml","packageKit")
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","pk.lu")
		#self.pkgFile="/usr/share/rebost/tmp/pk.rebost"
		self.pkgFile="/usr/share/rebost/lists.d/eduapps.map"
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		return
		if self.dbg==True:
			dbg="packagekit: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug

	def setOnlyFillMasterTable(self,force=True):
		self.onlyFillMaster=Force

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)
	#def execute

	def _loadStore(self,*args):
		action="load"
		pkcon=packagekit.Client()
		restrictIds=[]
		tmppkgIds=[]
		pkgIds=[]
		if self.restricted==False:
			flags=[packagekit.FilterEnum.APPLICATION,packagekit.FilterEnum.GUI]
			pklists=self._loadFullCatalogue(pkcon,flags)
		else:
			restrictIds=self._readFilterFile(self.pkgFile)
			pklists=self._loadRestrictedCatalogue(pkcon,restrictIds)
		for pkgSack in pklists:
			tmppkgIds.append(pkgSack.get_ids())
		if self.restricted==True:
			for pkglist in tmppkgIds:
				setlist=list(set(pkglist))
				for pkg in setlist:
					pkgname=pkg.split(";")[0]
					if pkgname not in restrictIds and "lliurex" not in pkgname.lower():
						pkgSack.remove_package_by_id(pkg)
		for pkgSack in pklists:
			pkgIds.extend(pkgSack.get_ids())
		if (len(pkgIds)>0):
			pkgUpdateIds={}
			self._debug("End Getting pkg list")
			self._processPackages(pkcon,pkgIds,pkgUpdateIds)
			self._debug("PKG loaded")
			try:
				with open(self.lastUpdate,'w') as f:
					f.write(newMd5)
			except:
				self._debug("Forcing update")
			self._debug("SQL loaded")
		else:
			self._debug("Skip update")
		return()
	#def _loadStore

	def _refreshPk(self,pkcon):
		self._debug("Refresh cache..")
		try:
			pkcon.refresh_cache(False,None,self._loadCallback,None)
		except:
			self._debug("apt seems blocked. Retrying...")
			try:
				pkcon.refresh_cache(False,None,self._loadCallback,None)
			except Exception as e:
				print(e)
	#def _refreshPk

	def _loadFullCatalogue(self,pkcon,flags=None):
		self._debug("Getting pkg list")
		pklists=[]
		if flags==None:
			flags=[packagekit.FilterEnum.NONE]
		if isinstance(flags,list)==False:
			flags=list(flags)
		for flag in flags:
			pkList=pkcon.get_packages(flag, None, self._loadCallback, None)
			pkgSack=pkList.get_package_sack()
			pklists.append(pkgSack)
		return (pklists)
	#def _loadFullCatalogue

	def _loadRestrictedCatalogue(self,pkcon,restrictedList):
		pklists=[]
		if len(restrictedList)>0:
			pkList=pkcon.resolve(packagekit.FilterEnum.NONE,restrictedList,None,self._loadCallback,None)
			pkgSack=pkList.get_package_sack()
			pklists.append(pkgSack)
		self._debug("Processing obtained list")
		return (pklists)
	#def _loadRestrictedCatalogue

	def _readFilterFile(self,pkgfile):
		self._debug("Getting restricted pkg list from {}".format(pkgfile))
		searchList=[]
		mapedList=[]
		if os.path.exists(pkgfile)==False:
			self._debug("File not found: {}".format(pkgfile))
		else:
			with open(pkgfile,"r") as f:
				jcontent=json.loads(f.read())
			searchList=[]
			for key,item in jcontent.items():
				mapedList.append(key)
				if item=="" or item in searchList:
					self._debug("Discard {}".format(key))
					continue
				searchList.append(item)
		searchList=self._addCacheFile(searchList,mapedList)
		return(searchList)
	#def _readFilterFile

	def _addCacheFile(self,pkglist=[],mapedList=[]):
		self._debug("Adding all packages from appsedu")
		eduApps=libAppsEdu.getAppsEduCatalogue()
		for pkg in eduApps:
			app=pkg["alias"].replace("zero:","").split(".")[-1].lower()
			if app not in pkglist and app not in mapedList:
				self._debug("Append unmaped app  {}".format(app))
				pkglist.append(app.lower())
				if app.lower().startswith("zero-")==False:
					zeroApp="zero-lliurex-{}".format(app.lower())
					self._debug("Append unmaped ZERO app  {}".format(zeroApp))
					pkglist.append(zeroApp)
		return(pkglist)
	#def _addCacheFile

	def _getChanges(self,gPath):
		#Compare old file with new file. Extract changes and update db
		oldPkgList=[]
		newPkgList=[]
		if os.path.isfile(self.pkgFile)==True:
			with open(self.pkgFile,'r') as f:
				oldPkgList=f.readlines()
		with open(gPath,'r') as f:
			newPkgList=f.readlines()
		shutil.copy(gPath,"/tmp/a")
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
				pkDetails=pkcon.get_details(selected, None, self._loadCallback, None)
				if pkDetails:
					self._debug("Sending to SQL")
					data=self._generateRebostPkgList(pkDetails,pkgUpdateIds)
					rebostHelper.rebostPkgsToSqlite(data,'packagekit.db',drop=False,sanitize=False)
			if updateSelected:
				self._debug("Updating {} items".format(len(updateSelected)))
				rebostHelper.rebostPkgsToSqlite(updateSelected,"packagekit.db")
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
			pkgToProcess=[pkg for pkg in pkgToProcess if "lliurex" in pkg.lower()]
		for pkg in pkgToProcess:
			#0->Name,1->Release,2->arch,3->origin
			pkgData=pkg.split(";")
			if pkgData[2]=="i386":
				continue
			pkgName=pkgData[0]
			pkgDict[pkgName]=pkg
		#Get rows for ids
		rows=[]
		if os.path.isfile(os.path.join(self.rebostCache,"packagekit.db")):
			rows=rebostHelper.getPkgFromTablearray("packagekit.db",list(pkgDict.keys()))
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
				updateSelected.append(rowData)
			elif ":" not in itemData[3] and rowData.get('state',{}).get('package',"1")!="1":
				rowData["state"]={"package":"1"}
				updateSelected.append(rowData)
		#Add non existent ids
		for pkg,item in pkgDict.items():
			selected.append(item)
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
		rebostPkg['id']=rebostPkg['name']
		rebostPkg['summary']=pkg.get_summary()
		rebostPkg['description']=pkg.get_description()
		updateVersion=updateInfo.get(name,{}).get('release',"{}".format(version))
		rebostPkg['versions']={"package":"{}".format(updateVersion)}
		rebostPkg['bundle']={"package":"{}".format(rebostPkg['name'])}
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
		elif os.path.isfile(os.path.join("/usr/share/icons/lliurex/apps/48","{0}.png".format(rebostPkg['name']))):
			rebostPkg['icon']=os.path.join("/usr/share/icons/lliurex/apps/48","{0}.png".format(rebostPkg['name']))
		return(rebostPkg)
	#def _generateRebostPkg

	def _generateRebostPkgList(self,pkgList,updateInfo):
		rebostPkgList=[]
		arr=pkgList.get_details_array()
		for pkg in arr:
			dismiss=["admin-tools","other","system"]
			#Dismiss disabled
			dismiss=[]
			cat=pkg.get_group().to_string(pkg.get_group()).lower().strip()
			#if (cat in dismiss==False) or ("lliurex" in pkg.get_url()):
			if (cat in dismiss==False) or ("zero-lliurex" in pkg.get_package_id()):
				pkgId=pkg.get_package_id().split(";")
				name=pkgId[0]
				#if name.startswith("zero-lliurex")==False:
				rebostPkg=self._generateRebostPkg(pkg,updateInfo)
				if rebostPkg["name"].startswith("zero-lliurex") and "installer" in rebostPkg["summary"].lower():# and rebostPkg['state']["package"]=="1":
					tmpPkg=rebostPkg.copy()
					rebostPkg['alias']=rebostPkg["name"]
					#rebostPkg['bundle'].update({"zomando":"{}".format(rebostPkg['alias'])})
					rebostPkg['state'].update({"zomando":"1"})
					rebostPkg['name']=rebostPkg["name"].replace("zero-lliurex-","")
					rebostPkgList.append(tmpPkg)
				rebostPkgList.append(rebostPkg)
		return(rebostPkgList)
	#def _generateRebostPkgList

	def _loadCallback(self,*args):
		return
	#def _loadCallback

def main():
	obj=packageKit()
	return(obj)

