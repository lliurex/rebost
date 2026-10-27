#!/usr/bin/python3
import sys,os
import traceback
import json
import concurrent.futures as Futures
import gi
from gi.repository import Gio
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream
from aux._config import _rebostConfig
from aux._extras import _rebostAux
from aux._plugins import _rebostPlugins
from aux._map import _rebostMap
DBG=True

class _RebostCore():
	def __init__(self,*args,**kwargs):
		self.DBG=DBG
		self.stores={}
		self.lastCheckedMapping=0
		self.config=_rebostConfig()
		self.appstream=appstream
		config=self.readConfig()
		self.CACHE=config["cache"]
		self.aux=_rebostAux(self)
		self.langs=self.aux.getLangs()
		self.map=_rebostMap(self)
		self._chkRelease()
		self._plugins=_rebostPlugins(self)
		self.plugins=self._loadPlugins()
		self.initProc=0
		self.store=appstream.Store()
		self.stores={"main":self.store}
		self.supportedformats=[]
		self.thExecutor=Futures.ThreadPoolExecutor(max_workers=4)
		self.ready=False
		self._debug("Supported formats: {}".format(self.supportedformats))
		#self._initCore()
	#def __init__

	def _debug(self,msg):
		if self.DBG==True:
			print("core: {}".format(msg))
	#def _debug

	def _error(self,e,msg=""):
		print("{}: {}\n<------ TRACEBACK ------>".format(msg,e))
		print(traceback.format_exc())
		print ("<------ TRACEBACK -----/>")
	#def _error

	def readConfig(self):
		return(self.config.readConfig())
	#def readConfig

	def _chkRelease(self):
		if self.aux.releaseChanged()==True:
			self._debug("--> RELEASE CHANGE DETECTED <--")
			self.aux.cleanFiles()
			self._debug("--> RELEASE CLEANED <--")
	#def _chkRelease(self):

	def _loadPlugins(self):
		self.supportedformats,plugins=self._plugins.loadPlugins()
		return(plugins)
	#def _loadPlugins

	def _toFile(self,store,fxml):
		store.to_file(Gio.File.parse_name(fxml),appstream.NodeToXmlFlags.FORMAT_MULTILINE|appstream.NodeToXmlFlags.FORMAT_INDENT)
	#def _toFile

	def _fromFile(self,store,fxml):
		self._debug("Attempt to load {} using {}".format(store,fxml))
		if os.path.exists(fxml):
			try:
				store.from_file(Gio.File.parse_name(fxml),None,None)
				self._debug("Added {} apps".format(store.get_size()))
			except Exception as e:
				self._debug("Malformed {}".format(fxml))
				self._aux.fixMalformedXml(fxml)
				self._debug("Updated {}".format(fxml))
				try:
					with open(fxml,"r") as f:
						fcontent=f.read()
					store.from_xml(fcontent)
					self._debug("Added {} apps".format(store.get_size()))
				except Exception as e:
					self._error(e,msg="Error fixing. Requires user intervention")
		else:
			self._debug("{} not found".format(fxml))
		return(store)
	#def _fromFile

	def _getVerifiedOrigins(self):
		return(self.config._getVerifiedOrigins(self.stores))
	#def _getVerifiedOrigins

	def _getOldData(self,app,donor):
		appDesc={}
		appSumm={}
		donorDesc={}
		donorSumm={}
		icon=None
		if app.get_icon_path()!=None:
			icon=app.get_icon_default()
		for l in self.langs:
			desc=app.get_description(l)
			if desc==None:
				desc=""
			summ=app.get_comment(l)
			if summ==None:
				summ=""
			appDesc.update({l:{"desc":desc,"summ":summ}})
			desc=donor.get_description(l)
			if desc==None:
				desc=""
			summ=donor.get_comment(l)
			if summ==None:
				summ=""
			donorDesc.update({l:{"desc":desc,"summ":summ}})
		return(appDesc,appSumm,donorDesc,donorSumm,icon)
	#def _getOldData

	def _doSubsumeApps(self,app,donor):
		#It seems strange but both subsumes are needed
		#add all info, honouring previous subsume
		#subsume_full will need lot of flags to load all the info, only put empty fields (including installed status aka metadata)
		appDesc,appSumm,donorDesc,donorSumm,icon=self._getOldData(app,donor)
		app.subsume(donor)
		extendFlags=appstream.AppSubsumeFlags.BUNDLES|\
			appstream.AppSubsumeFlags.METADATA|\
			appstream.AppSubsumeFlags.KEYWORDS|\
			appstream.AppSubsumeFlags.ICONS|\
			appstream.AppSubsumeFlags.URL|\
			appstream.AppSubsumeFlags.SCREENSHOTS
		app.subsume_full(donor,appstream.AppSubsumeFlags.BOTH_WAYS|extendFlags)
		replaceFlags=appstream.AppSubsumeFlags.STATE|\
				appstream.AppSubsumeFlags.NAME
		app.subsume_full(donor,appstream.AppSubsumeFlags.REPLACE|replaceFlags)
		for l,desc in donorDesc.items():
			if len(appDesc[l]["desc"])<len(desc["desc"]):
				app.set_description(l,desc["desc"])
			if len(appDesc[l]["summ"])<len(desc["summ"]):
				app.set_comment(l,desc["summ"])
		if icon!=None:
			app.add_icon(icon)
		app.subsume(donor)
		return(app)
	#def _doSubsumeApps

	def _preLoadVerified(self,verifiedOrigins):
		store=appstream.Store()
		for idx in verifiedOrigins:
			for app in self.stores[idx].get_apps():
				mergeApp=self._preMergeApp(app)
				oldApp=store.get_app_by_id(mergeApp.get_id())
				if oldApp!=None:
					store.remove_app(oldApp)
					try:
						mergeApp=self._doSubsumeApps(mergeApp,oldApp)
					except Exception as e:
						self._error(e,msg="_preLoadVerified")
				mergeApp.set_origin("verified")
				noDsp=self.mapFixes.get("nodisplay",[])
				appKnownAs=[mergeApp.get_id(),mergeApp.get_name()]
				appKnownAs.extend(mergeApp.get_pkgnames())
				allApps=list(set(noDsp))
				allApps.extend(list(set(appKnownAs)))
				if len(allApps) != len(set(allApps)):
					self._debug("Hidden -> {}".format(mergeApp.get_name()))
					mergeApp.add_metadata("X-REBOST-hidden","{}".format(mergeApp.get_id()))
				store.add_app(mergeApp)
		self._debug("Verified table count: {}".format(store.get_size()))
		return(store)
	#def _preLoadVerified

	def _preMergeApp(self,app):
		newId=app.get_id()
		aliases=self.mapFixes.get("aliases",{})
		if len(app.get_bundles())>0:
			if app.get_bundles()[0].get_kind()==appstream.BundleKind.FLATPAK:
				fixes=["gdevelop"]
				splitId=app.get_id().replace(".desktop","").split(".")
				newId=splitId[-1]
				if len(splitId)>2:
					if splitId[1].lower() in fixes:
						newId=splitId[1]
			elif app.get_bundles()[0].get_kind()==appstream.BundleKind.APPIMAGE:
				newId=app.get_id().strip()
				#Canonical name
				if newId.count("-")==2:
					newId=newId.split("-")[0]
				#Kdenlive (perhaps others)
				elif newId.count("_")==3:
					newId=newId.split("_")[0]
				else:
					tmpId=""
					while tmpId=="":
						arrayId=newId.strip().split(".")
						for item in arrayId:
							for i in item.split("-"):
								if i.isdigit():
									if tmpId!="":
										continue
								tmpId="{}.{}".format(tmpId,i)
					newId=tmpId.strip().rstrip(".").lstrip(".")
				newId=newId.lower().removesuffix(".appimage").split(".")[-1]
		#	elif app.get_bundles()[0].get_kind()==appstream.BundleKind.SNAP:
			else:
				newId=app.get_id().removesuffix(".desktop")
				if newId.count(".")>1: #It seems canonical
					tags=newId.split(".")
					tags.reverse()
					fallback=""
					for tag in tags:
						if tag.isnumeric():
							fallback=tag
							continue
						newId=tag
						break
		else:
			newId=app.get_id().removesuffix(".desktop")
			if newId.count(".")>1: #It seems canonical
				newId=newId.split(".")[-1]
		newId=newId.lower().removeprefix(".").removesuffix(".")
		if newId in aliases.keys():
			newId=aliases[newId]
		if newId!=app.get_id():
			app.set_id(newId)
		return (app)
	#def _preMergeApp

	def _mergeApps(self):
		self._debug("Filling work table")
		self.stores["mainB"]=appstream.Store() #Include all apps
		self.stores["mainB"].set_add_flags(appstream.StoreAddFlags.USE_MERGE_HEURISTIC) #Include verified apps
		verifiedOrigins=self._getVerifiedOrigins()
		self.mapFixes=self.getMapFixes()
		if len(verifiedOrigins)>0:
			self.stores["mainB"]=self._preLoadVerified(verifiedOrigins)
		self.ready=False
		self.stores["main"].remove_all()
		self.stores["main"].set_add_flags(appstream.StoreAddFlags.USE_MERGE_HEURISTIC)
		self.stores["main"].add_apps(self.stores["mainB"].dup_apps())
		aliases=self.mapFixes.get("aliases",{})
		for storeId in self.stores.keys():
			if storeId in verifiedOrigins:
				self._debug("Verified {}".format(storeId))
				continue
			if isinstance(storeId,int):
				self._debug("Process {} ({})".format(storeId,self.stores[storeId].get_size()))
				for app in self.stores[storeId].get_apps():
					appId=app.get_id()
					if appId in aliases.keys():
						self._debug("Change ID from {0} to {1}".format(appId,aliases[appId]))
						app.set_id(aliases[appId])
					originId=app.get_id()
					mergeApp=self._preMergeApp(app)
					tmpid=mergeApp.get_id()
					oldApp=self.stores["main"].get_app_by_id(tmpid)
					if oldApp==None:
						oldApp=self.stores["main"].get_app_by_id(originId.lower())
						if oldApp!=None:
							oldApp.set_id(tmpid)
					if oldApp!=None:
						try:
							self.stores["main"].remove_app(oldApp)
							mergeApp=self._doSubsumeApps(mergeApp,oldApp)
						except Exception as e:
							self._error(e,msg="_mergeApps")
					oldApp=self.stores["mainB"].get_app_by_id(tmpid)
					noDsp=self.mapFixes.get("nodisplay",[])
					appKnownAs=[mergeApp.get_id(),mergeApp.get_name()]
					appKnownAs.extend(mergeApp.get_pkgnames())
					allApps=list(set(noDsp))
					allApps.extend(list(set(appKnownAs)))
					if len(allApps) != len(set(allApps)):
						self._debug("Hidden -> {}".format(mergeApp.get_name()))
						mergeApp.add_metadata("X-REBOST-hidden","{}".format(mergeApp.get_id()))
					mergeApp.set_origin("unverified")
					if oldApp!=None:
						self.stores["mainB"].remove_app(oldApp)
						mergeApp.set_origin("verified")
						self.stores["mainB"].add_app(mergeApp)
					self.stores["main"].add_app(mergeApp)
		config=self.readConfig()
		if config.get("onlyVerified",False)==True:
			self.loadToggle()
	#def _mergeApps

	def loadToggle(self):
		tmp=self.stores["main"]
		if "mainB" in self.stores.keys():
			self.stores["main"]=self.stores["mainB"]
		self.stores["mainB"]=tmp
	#def _loadToggle

	def reload(self):
		self.aux.cleanFiles()
		self.lastCheckedMapping=0
		self.stores["main"].remove_all()
		if "mainB" in self.stores:
			self.stores["mainB"].remove_all()
		for storeId in self.stores.keys():
			self._debug("Process {}".format(storeId))
			if isinstance(storeId,int):
				self.stores[storeId].remove_all()
		self._debug("Reloading rebost core")
		self.ready=False
		self.stores={"main":self.store}
		self.initProc=0
		self.plugins=self._loadPlugins()
	#def reload(self):

	def export(self,fxml=""):
		if len(fxml.strip())==0:
			fxml=os.path.join(self.CACHE,"main.xml")
		try:
			self._toFile(self.stores["main"],fxml)
		except Exception as e:
			self._error(e,msg="export")
		return(fxml)
	#def export

	def _rebostOperative(self,*args):
		self.ready=True
		resultSet=args[0]
		if resultSet.done():
			if resultSet.exception():
				self._error(resultSet.exception(),msg="_rebostOperative")
		self._debug("Work table ready. Rebost is fully operative")
		self._debug("Loaded {} apps".format(self.stores["main"].get_size()))
		self._debug("Loaded {} appsB".format(self.stores["mainB"].get_size()))
		self.export()
	#def _rebostOperative

	def _callBackInit(self,*args,**kwargs):
		self._debug("Callback for {}".format(*args))
		storeId=len(self.stores)
		resultSet=args[0]
		self._debug("State {}".format(resultSet.done()))
		if resultSet.done():
			if resultSet.exception():
				self._error(resultSet.exception(),msg="_callBackInit")
			else:
				store=resultSet.result()
				self.stores.update({storeId:store})
		self.initProc-=1
		partial=0
		stores=self.stores.copy()
		for k in stores.keys():
			if isinstance(k,int):
				partial+=len(stores[k].get_apps())
		self._debug("Apps in store: {} Init({})".format(partial,self.initProc))
		if self.initProc==0:
			self._debug("Appstream tables ready. Rebost core operative")
			init=self.thExecutor.submit(self._mergeApps)
			init.add_done_callback(self._rebostOperative)
	#def _callBackInit(self,*args,**kwargs):

	def _initEngines(self):
		priorities=list(self.plugins.keys())
		priorities.sort()
		for priority in priorities:
			pluginfo=self.plugins[priority]
			for plugkey,plugmod in pluginfo.items():
				if isinstance(plugkey,appstream.BundleKind):
					self._debug((priority,plugkey))
					for mod in plugmod:
						init=self.thExecutor.submit(mod.getAppstreamData)
						self.initProc+=1
						init.add_done_callback(self._callBackInit)
	#def _initEngines

	def _loadFromCache(self):
		fxml=os.path.join(self.CACHE,"main.xml")
		try:
			cacheStore=self._fromFile(self.stores["main"],fxml)
		except Exception as e:
			self._error(e,msg="_loadFromCache")
			return
		if self.ready==False:
			self._debug("Loading {} apps from cache".format(cacheStore.get_size()))
			if cacheStore.get_size()>0:
				for app in cacheStore.get_apps():
					if len(app.get_kudos())>0:
						config=self.readConfig()
						if config.get("onlyVerified",False)==True:
							app.set_origin("verified")
				self.stores["main"]=cacheStore
				self._debug("Cached store loaded. Rebost will update data now")
				self.ready=True
	#def _loadFromCache

	def getExternalInstaller(self):
		config=self.readConfig()
		return(config.get("externalInstaller",""))
	#def getExternalInstaller

	def getMapFixes(self):
		return(self.map._getMapFixes())
	#def getMapFixes

	def chkCacheNeedsUpdate(self):
		return(self.map.chkCacheNeedsUpdate())
	#def chkCacheNeedsUpdate

	def initCore(self):
		#self.thExecutor.submit(self._loadFromCache)
		config=self.readConfig()
		if config.get("verifiedProvider","")!="":
			if config.get("onlyVerified",False)==True:
				print("\n******************************************************")
				print("************* RESTRICTED MODE ENABLED ****************")
				print("Verified origins {}".format(config["verifiedProvider"]))
				print("******************************************************\n")
		if len(self.stores)<=1 and self.initProc==0:
			self._loadFromCache()
			self._initEngines()
	#def _initCore
#class _RebostCore

