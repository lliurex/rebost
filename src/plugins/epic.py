#!/usr/bin/env python3
import os
import json
import html
import hashlib
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
from epi import epimanager
import gi
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit
DATA_DIR="/usr/share/rebost-data/lists.d/"
EDUAPPS_RELEASE="llx25"
if os.path.exists(DATA_DIR):
	for d in os.scandir(DATA_DIR):
		if d.name.startswith("llx"):
			EDUAPPS_RELEASE=d.name
			break
EDUAPPS_MAP=os.path.join(DATA_DIR,EDUAPPS_RELEASE,"eduapps.map")
EDUAPPS_MAP_URL="https://github.com/lliurex/rebost-data/raw/refs/heads/master/lists.d/{}/eduapps.map".format(EDUAPPS_RELEASE)

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.includedApps=[]
		self.bundle=self.core.appstream.BundleKind.UNKNOWN
		self.epiManager=epimanager.EpiManager()
		self.zmdDir="/usr/share/zero-center/zmds"
		self.appDir="/usr/share/zero-center/applications"
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("epic: {}".format(msg))
	#self _debug

	def _sectionMap(self,section):
		section=section.replace("desktop-","")
		sectionMap={"Multimedia":"AudioVideo","FP":"Education","Resources":"Education","System":"System","Software":"Utility","Support":"System","Internet":"Network","Services":"System"}
		return(sectionMap.get(section,"Utility"))
	#def _sectionMap

	def _fetchCatalogue(self,url=""):
		if len(url)==0:
			url=EDUAPPS_URL
		content=''
		req=Request(url, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urllib.request.urlopen(req,timeout=2) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			self._debug("Couldn't fetch {}".format(url))
			self._debug(e)
		return(content)
	#def _fetchCatalogue

	def _getAppseduMapFixes(self):
		mapFixes={"nodisplay":[],"alias":{}}
		jcontent={}
		if os.path.exists(EDUAPPS_MAP):
			with open(EDUAPPS_MAP,"r") as f:
				mapFixes=json.loads(f.read())
		mapFixesUrlContent=self._fetchCatalogue(EDUAPPS_MAP_URL)
		if len(mapFixesUrlContent)>0:
			try:
				jcontent=json.loads(mapFixesUrlContent)
			except Exception as e:
				print(e)
				jcontent={}
		if len(jcontent)>0:
			if jcontent!=mapFixes:
				jcontentNodisplay=jcontent.get("nodisplay",[])
				nodisplay=list(set(mapFixes["nodisplay"]+jcontentNodisplay))
				mapFixes["nodisplay"]=nodisplay
				jcontentAliases=jcontent.get("aliases",{})
				mapFixes["aliases"].update(jcontentAliases)
		return(mapFixes)
	#def _getAppseduMapFixes


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
		matchName=name
		candidateDirs=["/usr/share/banners/lliurex-neu",os.path.join("/usr/share","{}".format(name)),os.path.join("/usr/share","{}".format(name.replace("zero-lliurex-","")))]
		for candidateDir in candidateDirs:
			if os.path.exists(candidateDir):
				try:
					for candidateF in os.scandir(candidateDir):
						candidateExt=candidateF.name.split(".")[-1]
						candidateName=".".join(candidateF.name.split(".")[:-1])
						if candidateExt in ["png","svg"]:
							if matchName in candidateName:
								appicon=self.core.appstream.Icon()
								appicon.set_kind(self.core.appstream.IconKind.LOCAL)
								appicon.set_name(candidateName)
								appicon.set_filename(candidateF.path)
								break
				except Exception as e: #Permissions error
					self._debug(e)
			if appicon!=None:
				break
		return (appicon)
	#get _getIcon

	def _getIncludedApps(self,epiName,epiData):
		apps=[]
		seen=[]
		pkgList=epiData.get("pkg_list",[])
		pkgList.extend(epiData.get("only_gui_available",[]))
		if len(pkgList)>0:
			epiInfo=self._getEpiInfo(epiName,epiData["zomando"])
			for pkg in pkgList:
				suggested=[]
				if pkg["name"] not in epiInfo:
					continue
				app=self.core.appstream.App()
				#suggest=self.core.appstream.Suggest()
				#suggest.set_kind(self.core.appstream.SuggestKind.UPSTREAM)
				pkgid=pkg.get("name").split(" ")[0].rstrip(",").rstrip(".").rstrip(":")
				name=pkg.get("custom_name",pkg["name"])
				self.includedApps.append(name)
				app.set_id(pkgid)
				app.set_name("C",name)
				app.set_comment("C",name)
				app.set_description("C","Included in {}".format(epiName.replace(".epi","")))
				app.add_pkgname(pkgid)
				app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
				app.add_url(self.core.appstream.UrlKind.HELP,"")
				customIcon=pkg.get("custom_icon")
				customIconPath=epiData.get("custom_icon_path")
				if customIcon!=None and customIconPath!=None:
					icn=os.path.join(customIconPath,customIcon)
					appicon=self.core.appstream.Icon()
					appicon.set_kind(self.core.appstream.IconKind.LOCAL)
					appicon.set_name(customIcon)
					appicon.set_filename(icn)
					app.add_icon(icn)
				bundles=app.get_bundles()
				if len(bundles)==0:
					bun=self.core.appstream.Bundle()
					bun.set_kind(self.core.appstream.BundleKind.UNKNOWN)
					bun.set_id(epiName)
					app.add_bundle(bun)
				app.add_keyword("C",epiData["zomando"])
				for keyword in epiData["zomando"].split("-"):
					app.add_keyword("C",keyword)
				#suggest.add_id(epiData["zomando"])
				#app.add_suggest(suggest)
				if app.get_id() not in seen:
					apps.append(app)
					seen.append(app.get_id())
		else:
			self._debug("No packages found for {}".format(fname))
		return(apps)
	#def _getIncludedApps

	def _getCategoriesFromEpi(self,appName):
		categories=[]
		if appName.startswith("zero-")==False and appName.startswith("llx")==False:
			appName="zero-lliurex-{}".format(appName)
		fpath="/usr/share/zero-center/applications/{}".format(appName)
		if os.path.exists(fpath):
			with open(fpath,"r") as f:
				fcontent=f.read()
			for fline in fcontent.split("\n"):
				if fline.startswith("Category"):
					cat=fline.split("=")[-1].strip()
					cat=self._sectionMap(cat.capitalize())
					categories.append(cat)
					break
		return(categories)
	#def _getCategoriesFromEpi

	def _getAppsFromEpic(self,epicList,mapFixes):
		apps=[]
		names=[]
		for epi in epicList:
			for epiName,epiData in epi.items():
				suggested=[]
				suggest=self.core.appstream.Suggest()
				includedCategories=[]
				self._debug("Processing {} ({})".format(epiName,len(epiData)))
				fname=epiData.get("zomando")
				if len(fname)>0:
					app=self.core.appstream.App()
					name=os.path.basename(fname).replace(".zmd","")
					if name in mapFixes["nodisplay"] or fname in mapFixes["nodisplay"]:
						self._debug("Discard {}".format(name))
						continue
					app.set_id(name)
					app.add_pkgname(fname)
					app.add_keyword("C",fname)
					app.add_keyword("C","zomando")
					app.add_keyword("C","zomandos")
					app.set_state(self.core.appstream.AppState.INSTALLED)
					icn=self._getIcon(name)
					if icn!=None:
						app.add_icon(icn)
					summary=epiData.get("custom_name",os.path.basename(fname).replace(".zmd",""))
					description=summary
					includedApps=self._getIncludedApps(epiName,epiData)
					if len(includedApps)>1:
						app.add_suggest(suggest)
					for includedApp in includedApps:
						if includedApp.get_id()=="" or includedApp.get_id()==None:
							continue
						#app.add_keyword("C",includedApp.get_id())
						apps.append(includedApp)
						description+="\n    - {}".format(includedApp.get_id())
						if includedApp.get_id() in suggested:
							continue
						suggest.add_id(includedApp.get_id())
						suggested.append(includedApp.get_id())
					for l in self.core.langs:
						app.set_name(l,os.path.basename(fname).replace(".zmd",""))
						app.set_comment(l,summary)
						app.set_description(l,description)
					app.set_name("C",os.path.basename(fname).replace(".zmd",""))
					app.set_comment("C",summary)
					app.set_description("C",description)
					app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
					app.add_url(self.core.appstream.UrlKind.HELP,"https://wiki.edu.gva.es/lliurex/tiki-index.php")
					bun=self.core.appstream.Bundle()
					bun.set_kind(self.core.appstream.BundleKind.UNKNOWN)
					bun.set_id(fname)
					app.add_bundle(bun)
					apprelease=self.core.appstream.Release()
					apprelease.set_version("1.0")
					apprelease.set_state(self.core.appstream.ReleaseState.INSTALLED)
					app.set_state(self.core.appstream.AppState.INSTALLED)
					app.add_release(apprelease)
					#Category
					appName=os.path.basename(fname).replace(".zmd","")+".app"
					categories=self._getCategoriesFromEpi(appName)
					for cat in categories:
						app.add_category(cat)
					apps.append(app)
				else:
					self._debug("Not found {}".format(fname))
		return(apps)
	#def _getAppsFromEpic

	def _loadCallback(self,*args):
		return
	#def _loadCallback

	def _getAppsFromSystem(self):
		flags=packagekit.FilterEnum.NONE
		pk=packagekit.Client()
		pkListSack=[]
		searchValue="zero-"
		pkList=pk.get_packages(flags,None,self._loadCallback,None)
		pkSack=pkList.get_package_array()
		for pk in pkSack:
			if pk.get_id().split(";")[0].startswith(searchValue):
				if "zero-center" in pk.get_id():
					continue
				pkListSack.append(pk)
		return(pkListSack)
	#def _getAppsFromSystem

	def _chkNeedUpdate(self,apps):
		#Force updates
		update=True
		#cont=len(apps)
		#chash=hashlib.md5(str(cont).encode("utf8")).hexdigest()
		#frepo=os.path.join(self.cache,"epic")
		#if os.path.isfile(frepo):
		#	fcontent=""
		#	with open(frepo,'r') as f:
		#		fhash=f.read()
		#	if chash==fhash:
		#		update=False
		#	self._debug(fhash)
		#self._debug(chash)
		#with open(frepo,'w') as f:
		#	f.write(chash)
		return(update)
	#def _chkNeedUpdate

	def getAppstreamData(self):
		fxml=os.path.join(self.cache,"epic.xml")
		store=self.core.appstream.Store()
		store.set_add_flags(self.core.appstream.StoreAddFlags.USE_UNIQUE_ID)
		store.set_origin("epic")
		mapFixes=self._getAppseduMapFixes()
		epicList=self.epiManager.all_available_epis
		if self._chkNeedUpdate(epicList)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			lstApps=self._getAppsFromEpic(epicList,mapFixes)
			store.add_apps(lstApps)
			pkgs=self._getAppsFromSystem()
			for pkg in pkgs:
				pkgId=pkg.get_id()
				if pkgId.split(";")[0] in mapFixes["nodisplay"] or pkg.get_name() in mapFixes["nodisplay"]:
					self._debug("Discard {}".format(pkg.get_id()))
					continue
				pkgIdArray=pkgId.split(";")
				name=pkgIdArray[0]
				release=pkgIdArray[1]
				origin=pkgIdArray[2]
				arch=pkgIdArray[3]
				app=store.get_app_by_id(name)
				if app==None:
					app=self.core.appstream.App()
					app.set_id(name)
					app.add_pkgname(name)
					desc=html.escape(pkg.get_summary().strip())
					app.set_description("C",desc)
					summary=desc.split("\n")[0]
					app.set_comment("C",summary)
					#app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
				else:
					store.remove_app(app)
				if "auto:" in pkgId or "manual:" in pkgId or "installed" in pkgId:
					app.add_metadata("X-REBOST-package","{};{}".format(release,"installed"))
				bun=self.core.appstream.Bundle()
				bun.set_kind(self.core.appstream.BundleKind.PACKAGE)
				bun.set_id(name)
				app.add_bundle(bun)
				store.add_app(app)
			self.core._toFile(store,fxml)
		self._debug("Sending {}".format(store.get_size()))
		return(store)
	#def getAppstreamData

	def refreshAppData(self,app):
		#epic has states but from rebost point of view they're always installed
		return(app)
	#def refreshAppData(self,app):
#class engine
