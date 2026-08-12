#!/usr/bin/env python3
import os,subprocess
from random import shuffle
import json
import html
from urllib import request
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
		#Fix epic needing known user
		if os.environ.get("USER",None)==None:
			os.environ["USER"]="root"
		self.epiManager=epimanager.EpiManager()
		self.name="epic"
		self.zmdDir="/usr/share/zero-center/zmds"
		self.appDir="/usr/share/zero-center/applications"
		self.noAppend=[]
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
		self._debug("Fetching {}".format(url))
		content=''
		req=request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with request.urlopen(req,timeout=2) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			self._debug("Couldn't fetch {}".format(url))
			self._debug(e)
		return(content)
	#def _fetchCatalogue

	def _getEpiInfo(self,epiName,zmdName):
		epiInfo={}
		zmdName=zmdName.replace(".epi","")
		epiPath=os.path.join("/","usr","share",zmdName,epiName)
		if os.path.exists(epiPath):
			with open (epiPath,"r") as f:
				epiInfo=json.load(f)
		pkgInfoList=epiInfo.get("pkg_list",[])
		for pkgItem in pkgInfoList:
			name=pkgItem.pop("name").strip()
			epiInfo.update({name:pkgItem})
		return epiInfo
	#def _getEpiInfo

	def _setDefaultInfo(self,app,pkg,epiName):
		summary=pkg.get("custom_name",pkg["name"])
		name=pkg["name"].strip()
		if name.count(".")>1:
			name=name.split(".")[-1]
		app.set_name("C",name)
		app.set_comment("C",summary)
		app.set_description("C","Included in {}".format(epiName))
		app.add_pkgname(app.get_id())
		app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
		app.add_url(self.core.appstream.UrlKind.HELP,"")
	#def _setDefaultInfo

	def _getIcon(self,fname):
		name=os.path.basename(fname).replace(".zmd","")
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

	def _setIcon(self,app,pkg):
		customIcon=pkg.get("custom_icon")
		if customIcon!=None:
			customIconPath=epiData.get("custom_icon_path")
			if customIconPath==None:
				zmdName=epiData["zomando"]
				zmdName=zmdName.replace(".epi","")
				epiPath=os.path.join("/","usr","share",zmdName,epiName)
				customIconPath=os.path.dirname(epiPath)
			icn=os.path.join(customIconPath,customIcon)
			appicon=self.core.appstream.Icon()
			appicon.set_kind(self.core.appstream.IconKind.LOCAL)
			appicon.set_name(customIcon)
			appicon.set_filename(icn)
			app.add_icon(appicon)
	#def _setIcon

	def _getBundleKind(self,epiType):
		if epiType in ["apt","deb"]:
			epiType="package"
		bundles={"flatpak":self.core.appstream.BundleKind.FLATPAK,\
			"snap":self.core.appstream.BundleKind.SNAP,\
			"appimage":self.core.appstream.BundleKind.APPIMAGE,\
			"package":self.core.appstream.BundleKind.PACKAGE}
		bundle=bundles.get(epiType,self.core.appstream.BundleKind.UNKNOWN)
		return(bundle)
	#def _getBundleKind

	def _setBundleKind(self,app,epiName,epiInfo):
		pkgid=app.get_id()
		bundles=app.get_bundles()
		if len(bundles)==0:
			bun=self.core.appstream.Bundle()
			if "snap" in pkgid.lower():
				sna=self.core.appstream.Bundle()
				sna.set_kind(self.core.appstream.BundleKind.SNAP)
				sna.set_id(pkgid)
				app.add_bundle(sna)
			elif "flatpak" in pkgid.lower():
				flt=self.core.appstream.Bundle()
				flt.set_kind(self.core.appstream.BundleKind.FLATPAK)
				flt.set_id(pkgid)
				app.add_bundle(flt)
			elif "appimage" in pkgid.lower():
				aim=self.core.appstream.Bundle()
				aim.set_kind(self.core.appstream.BundleKind.APPIMAGE)
				aim.set_id(pkgid)
				app.add_bundle(aim)
			elif pkgid!=epiName:
				ebu=self.core.appstream.Bundle()
				bundle=self._getBundleKind(epiInfo.get("type",""))
				if bundle!=self.core.appstream.BundleKind.UNKNOWN:
					ebu.set_kind(bundle)
					ebu.set_id(pkgid)
					app.add_bundle(ebu)
			bun.set_kind(self.core.appstream.BundleKind.UNKNOWN)
			bun.set_id(epiName)
			app.add_bundle(bun)
	#def _setBundleKind

	def _getIncludedApps(self,epiName,epiData):
		apps=[]
		seen=[]
		if epiData.get("zomando")==None:
			return apps
		pkgList=epiData.get("pkg_list",[])
		pkgList.extend(epiData.get("only_gui_available",[]))
		if len(pkgList)>0:
			epiInfo=self._getEpiInfo(epiName,epiData["zomando"])
			for pkg in pkgList:
				app=self.core.appstream.App()
				pkg["name"]=pkg["name"].strip()
				pkgid=pkg.get("name").split(" ")[0].rstrip(",").rstrip(".").rstrip(":")
				app.set_id(pkgid)
				self._setDefaultInfo(app,pkg,epiName)
				self._setIcon(app,epiData)
				self._setBundleKind(app,epiName,epiInfo)
				if app.get_id() not in seen:
					apps.append(app)
					seen.append(app.get_id())
		else:
			self._debug("No packages found for {}".format(fname))
		return(apps)
	#def _getIncludedApps

	def _getIdFromZmd(self,epiName):
		epiId=epiName
		if epiName.startswith("zero-"):
			epiId="zero.lliurex.{}".format("-".join(epiName.split("-")[2:])).removesuffix(".epi")
		else:
			epiId="zero.lliurex.{}".format(epiName).removesuffix(".epi")
		return(epiId)
	#def _getIdFromZmd

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

	def _addDefaultKeywords(self,fname,zmd,app):
		fname=fname.removesuffix(".epi")
		zmd=zmd.removesuffix(".epi")
		app.add_keyword("C",fname)
		if zmd!=fname:
			app.add_keyword("C",zmd)
		last=zmd.split("-")[-1]
		if last!=zmd:
			app.add_keyword("C",last)
		return(app)
	#def _addDefaultKeywords

	def _addSuggestedApps(self,includedApps,app):
		if len(includedApps)>1:
			suggested=[]
			suggest=self.core.appstream.Suggest()
			for includedApp in includedApps:
				appId=includedApp.get_id()
				if appId not in suggested:
					suggested.append(appId)
			shuffle(suggested)
			for suggestApp in suggested[0:min(5,len(suggested))]:
				suggest.add_id(suggestApp)
			app.add_suggest(suggest)
		return(app)
	#def _addSuggestedApps(self,app,includedApps):

	def _appendIncludedApps(self,includedApps,app):
		apps=[]
		if len(includedApps)==1:
			includedApps[0].subsume(app)
		for includedApp in includedApps:
			if includedApp.get_id()=="" or includedApp.get_id()==None:
				continue
			#app.add_keyword("C",includedApp.get_id())
			apps.append(includedApp)
			self._addDefaultKeywords("",app.get_name("C"),includedApp)
		return(apps)
	#def _appendIncludedApps

	def _addExtendedInfo(self,epiData,app,apps):
		if len(epiData.get("pkg_list",[]))==1:
			summary=epiData["pkg_list"][0].get("custom_name",epiData.get("zomando"))
		else:
			summary=epiData.get("custom_name",epiData.get("zomando"))
		suggests=""
		if len(apps)>0:
			suggests=":"
			for suggest in apps:
				suggests+="\n - {}".format(suggest.get_name("C"))
		description=summary+suggests
		for l in self.core.langs:
			app.set_name(l,epiData.get("zomando",app.get_id()))
		app.set_name("C",epiData.get("zomando",app.get_id()))
		app.set_comment("C",summary)
		app.set_description("C",description)
		app.add_url(self.core.appstream.UrlKind.HOMEPAGE,"https://github.com/lliurex")
		app.add_url(self.core.appstream.UrlKind.HELP,"https://wiki.edu.gva.es/lliurex/tiki-index.php")
	#def _addExtendedInfo

	def _addBundle(self,fname,app):
		bun=self.core.appstream.Bundle()
		bun.set_kind(self.core.appstream.BundleKind.UNKNOWN)
		bun.set_id(fname)
		app.add_bundle(bun)
	#def _addBundle

	def _addRelease(self,app):
		apprelease=self.core.appstream.Release()
		apprelease.set_version("zomando")
		apprelease.set_state(self.core.appstream.ReleaseState.INSTALLED)
		app.set_state(self.core.appstream.AppState.INSTALLED)
		app.add_release(apprelease)
	#def _addRelease

	def _addCategoriesFromAppFile(self,fname,app):
		#Category
		appName=os.path.basename(fname).replace(".zmd","")+".app"
		categories=self._getCategoriesFromEpi(appName)
		for cat in categories:
			app.add_category(cat)
	#def _addCategoriesFromAppFile

	def _getAppsFromEpic(self,epicList):
		apps=[]
		for epi in epicList:
			#Each epi is an app by itself but it could be:
			# - MetaZomando: Zomando that installs more than one app
			# - Installer: Zomando that performs the install of an app
			# - Auxiliary: Zomandos that don't do anything special 
			for epiName,epiData in epi.items():
				self._debug("Processing {} ({})".format(epiName,len(epiData)))
				fname=epiData.get("zomando")
				if len(fname)>0:
					app=self.core.appstream.App()
					app.set_id(self._getIdFromZmd(epiName))
					app.add_pkgname(fname)
					self._addDefaultKeywords(fname,epiData["zomando"],app)
					app.set_state(self.core.appstream.AppState.INSTALLED)
					icn=self._getIcon(fname)
					if icn!=None:
						app.add_icon(icn)
					includedApps=self._getIncludedApps(epiName,epiData)
					self._addExtendedInfo(epiData,app,includedApps)
					apps.extend(self._appendIncludedApps(includedApps,app))
					self._addSuggestedApps(apps,app)
					self._addBundle(fname,app)
					self._addRelease(app)
					self._addCategoriesFromAppFile(fname,app)
					if len(includedApps)>=1:
						apps.append(app)
						if len(includedApps)==1:
							self.noAppend.append(fname)
						else:
							app.add_category("zomando")
				else:
					self._debug("Not found {}".format(fname))
		return(apps)
	#def _getAppsFromEpic

	def _loadCallback(self,*args):
		return
	#def _loadCallback

	def _getPkgSack(self,searchValue="zero-"):
		flags=packagekit.FilterEnum.NONE
		pk=packagekit.Client()
		pkListSack=[]
		pkSack=[]
		try:
			pkList=pk.get_packages(flags,None,self._loadCallback,None)
			pkSack=pkList.get_package_array()
		except:
			try:
				pkList=pk.get_packages(flags,None,self._loadCallback,None)
				pkSack=pkList.get_package_array()
			except:
				pass
		for pk in pkSack:
			if pk.get_id().split(";")[0].startswith(searchValue):
				if "zero-center" in pk.get_id():
					continue
				pkListSack.append(pk)
		return(pkListSack)
	#def _getPkgSack

	def _getAppFromPkg(self,pkg,appId,name):
		app=self.core.appstream.App()
		app.set_id(appId)
		app.add_pkgname(name)
		desc=html.escape(pkg.get_summary().strip())
		app.set_description("C",desc)
		summary=desc.split("\n")[0]
		app.set_comment("C",summary)
		bun=self.core.appstream.Bundle()
		bun.set_kind(self.core.appstream.BundleKind.PACKAGE)
		bun.set_id(name)
		app.add_bundle(bun)
		return(app)
	#def _getAppFromPkg

	def _getAppsFromSystem(self,store):
		pkgSack=self._getPkgSack()
		apps=[]
		for pkg in pkgSack:
			pkgInfo=pkg.get_id()
			name,release,origin,arch=pkgInfo.split(";")
			if name.count("-")==1:
				continue
			appId=self._getIdFromZmd(name)
			#If exists discard
			if store.get_app_by_id(appId):
				continue
			apps.append(self._getAppFromPkg(pkg,appId,name))
		return(apps)
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

	def _storeFromCache(self,fxml):
		store=self.core.appstream.Store()
		store.set_add_flags(self.core.appstream.StoreAddFlags.USE_UNIQUE_ID)
		store.set_origin("epic")
	#	if self._chkNeedUpdate(epicList)==False:
	#		self._debug("Loading from cache")
	#		store=self.core._fromFile(store,fxml)
		return(store)
	#def _storeFromCache

	def getAppstreamData(self):
		fxml=os.path.join(self.cache,"epic.xml")
		store=self._storeFromCache(fxml)
		if len(store.get_apps())==0:
			availableEpis=self.epiManager.all_available_epis
			epiApps=self._getAppsFromEpic(availableEpis)
			store.add_apps(epiApps)
			pkgApps=self._getAppsFromSystem(store)
			store.add_apps(pkgApps)
		self.core._toFile(store,fxml)
		return store
	#def getAppstreamData

	def refreshAppData(self,app):
		#epic has states but from rebost point of view they're always installed
		bundles=app.get_bundles()
		zmd=""
		for bundle in bundles:
			if bundle.get_kind()==self.core.appstream.BundleKind.UNKNOWN:
				zmd=bundle.get_id()
				break
		
		if zmd!="":
			zmd="{}.epi".format(zmd.removesuffix(".epi"))
			pkg=app.get_pkgname_default()
			if isinstance(pkg,str):
				cmd=["epic","showinfo",zmd]
				try:
					output=subprocess.check_output(cmd,encoding="utf8",universal_newlines=True)
				except:
					cmd=["epic","showinfo",os.path.basename(zmd.replace("zero-lliurex-",""))]
					try:
						output=subprocess.check_output(cmd,encoding="utf8",universal_newlines=True)
					except:
						output=""
				status="available"
				for l in output.split("\n"):
					if pkg in l:
						if "already installed" in l.lower():
							status="installed"
							break
					elif "status: installed" in l.lower():
						status="installed"
						break
				if status=="installed":
					app.set_state(self.core.appstream.AppState.INSTALLED)
				else:
					app.set_state(self.core.appstream.AppState.AVAILABLE)
				metastatus=app.get_metadata_item("X-REBOST-package")
				if metastatus!=None:
					app.remove_metadata("X-REBOST-package")
				app.add_metadata("X-REBOST-package","1;{}".format(status))
		return(app)
	#def refreshAppData(self,app):
#class engine
