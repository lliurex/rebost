#!/usr/bin/env python3
import os
import json
import html
import hashlib
from epi import epimanager
import gi
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.bundle=self.core.appstream.BundleKind.UNKNOWN
		self.epiManager=epimanager.EpiManager()
		self.zmdDir="/usr/share/zero-center/zmds"
		self.appDir="/usr/share/zero-center/applications"
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("epic: {}".format(msg))
	#self _debug

	def _getEpiInfo(self,epiName,zmdName):
		epiInfo={}
		zmdName=zmdName.replace(".epi","")
		epiPath=os.path.join("/","usr","share",zmdName,epiName)
		if os.path.exists(epiPath):
			with open (epiPath,"r") as f:
				epiInfo=json.load(f)
		pkgInfoList=epiInfo.get("pkg_list",[])
		for pkgItem in pkgInfoList:
			name=pkgItem.pop("name")
			epiInfo.update({name:pkgItem})
		return epiInfo
	#def _getEpiInfo

	def _getIcon(self,name):
		appicon=None
		candidateDirs=["/usr/share/banners/lliurex-neu",os.path.join("/usr/share","{}".format(name)),os.path.join("/usr/share","{}".format(name.replace("zero-lliurex-","")))]
		for candidateDir in candidateDirs:
			if os.path.exists(candidateDir):
				try:
					for l in os.scandir(candidateDir):
						if (app.get_id().replace(".epi","").split(".")[-1] in l.name ) and (l.name.endswith("png") or l.name.endswith(".svg")):
							appicon=self.core.appstream.Icon()
							appicon.set_kind(self.core.appstream.IconKind.LOCAL)
							appicon.set_name(os.path.basename(icn))
							appicon.set_file(icn)
							break
				except: #Permissions error
					continue
			if appicon!=None:
				break
		return (appicon)
	#get _getIcon

	def _getIncludedApps(self,epiName,epiData):
		apps=[]
		pkgList=epiData.get("pkg_list",[])
		pkgList.extend(epiData.get("only_gui_available",[]))
		if len(pkgList)>0:
			epiInfo=self._getEpiInfo(epiName,epiData["zomando"])
			for pkg in pkgList:
				if pkg["name"] not in epiInfo:
					continue
				app=self.core.appstream.App()
				pkgid=pkg.get("name").split(" ")[0].rstrip(",").rstrip(".").rstrip(":")
				name=pkg.get("custom_name",pkg["name"])
				app.set_id(pkgid)
				for l in self.core.langs:
					app.set_name(l,name)
					app.set_comment(l,name)
				app.add_pkgname(pkgid)
				customIcon=pkg.get("custom_icon")
				customIconPath=epiData.get("custom_icon_path")
				if customIcon!=None and customIconPath!=None:
					appicon=self.core.appstream.Icon()
					appicon.set_kind(self.core.appstream.IconKind.LOCAL)
					appicon.set_name(os.path.basename(icn))
					appicon.set_file(os.path.join(customIconPath,customIcon))
					app.add_icon(icn)
				#if epiInfo[pkg["name"]]['status']=="installed":
				#	state="0"
				bun=self.core.appstream.Bundle()
				epiType=epiInfo[pkg["name"]].get("type","apt")
				if epiType=="apt":
					bun.set_kind(self.core.appstream.BundleKind.PACKAGE)
				elif epiType=="flatpak":
					bun.set_kind(self.core.appstream.BundleKind.FLATPAK)
				elif epiType=="snap":
					bun.set_kind(self.core.appstream.BundleKind.SNAP)
				elif epiType=="appimage":
					bun.set_kind(self.core.appstream.BundleKind.APPIMAGE)
				bun.set_id(app.get_pkgname_default())
				app.add_bundle(bun)
				apps.append(app)
		else:
			print("No packages found for {}".format(fname))
		return(apps)
	#def _getIncludedApps

	def _getAppsFromEpic(self,epicList):
		apps=[]
		for epi in epicList:
			for epiName,epiData in epi.items():
				self._debug("Processing {} ({})".format(epiName,len(epiData)))
				fname=epiData.get("zomando")
				if len(fname)>0:
					app=self.core.appstream.App()
					name=os.path.basename(fname).replace(".zmd","")
					app.set_id(name)
					app.add_pkgname(fname)
					for l in self.core.langs:
						app.set_name(l,os.path.basename(fname).replace(".zmd",""))
						summary=epiData.get("custom_name",os.path.basename(fname).replace(".zmd",""))
						app.set_comment(l,summary)
						app.set_description(l,summary)
					app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
					bun=self.core.appstream.Bundle()
					bun.set_kind(self.core.appstream.BundleKind.UNKNOWN)
					bun.set_id(fname)
					app.add_bundle(bun)
					icn=self._getIcon(name)
					if icn!=None:
						app.add_icon(icn)
					apps.extend(self._getIncludedApps(epiName,epiData))
					apps.append(app)
		return(apps)
	#def _getAppsFromEpic

	def _loadCallback(self,*args):
		return
	#def _loadCallback

	def _getAppsFromSystem(self):
		flags=packagekit.FilterEnum.GUI
		pk=packagekit.Client()
		pkList=pk.search_names(flags,"zero-",None,self._loadCallback)
		return(pkList.get_package_array())
	#def _getAppsFromSystem

	def _chkNeedUpdate(self,apps):
		update=True
		cont=len(apps)
		chash=hashlib.md5(str(cont).encode("utf8")).hexdigest()
		frepo=os.path.join(self.cache,"epic")
		if os.path.isfile(frepo):
			fcontent=""
			with open(frepo,'r') as f:
				fhash=f.read()
			if chash==fhash:
				update=False
			self._debug(fhash)
		self._debug(chash)
		with open(frepo,'w') as f:
			f.write(chash)
		return(update)
	#def _chkNeedUpdate

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		action="load"
		epicList=self.epiManager.all_available_epis
		apps=self._getAppsFromSystem()
		fxml=os.path.join(self.cache,"epic.xml")
		if self._chkNeedUpdate(apps+epicList)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			store.add_apps(self._getAppsFromEpic(epicList))
			for pkg in apps:
				pkgId=pkg.get_id().split(";")
				name=pkgId[0]
				release=pkgId[1]
				origin=pkgId[2]
				arch=pkgId[3]
				if name.startswith("zero"):
					if not "lliurex" in name.lower() and not "installer" in name.lower():
						continue
					app=store.get_app_by_id(name)
					if app==None:
						app=self.core.appstream.App()
						app.set_id(name)
						desc=html.escape(pkg.get_summary().strip())
						app.set_description("C",desc)
						summary=desc.split("\n")[0]
						app.set_comment("C",summary)
						app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
						store.add_app(app)
					bun=self.core.appstream.Bundle()
					bun.set_kind(self.core.appstream.BundleKind.PACKAGE)
					bun.set_id(name)
					app.add_bundle(bun)
			self.core._toFile(store,fxml)
		return(store)
	#def getAppstreamData
