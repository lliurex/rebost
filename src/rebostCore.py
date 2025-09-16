#!/usr/bin/python3
import sys,os,time
import traceback
import json
import importlib.util
import xml.etree.ElementTree as ET
import html
import locale
import concurrent.futures as Futures
import gi
from gi.repository import Gio
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream

DBG=True
SCHEMES=os.path.join(os.path.dirname(os.path.realpath(__file__)),"schemes")
WRKDIR=os.path.join(os.environ["HOME"],".local","share","rebost")
DBDIR=os.path.join(WRKDIR,"data")
CACHE=os.path.join(os.environ["HOME"],".cache","rebost")
CONFIG="/usr/share/rebost/rebost.conf"


class _RebostCore():
	def __init__(self,*args,**kwargs):
		self.dbg=DBG
		self.SCHEMES=SCHEMES
		self.WRKDIR=WRKDIR
		self.DBDIR=DBDIR
		self.CACHE=CACHE
		self.DBG=DBG
		self.appstream=appstream
		self.stores={}
		self.initProc=0
		self.store=appstream.Store()
		self.stores={"main":self.store}
		self.supportedformats=[]
		self.thExecutor=Futures.ThreadPoolExecutor(max_workers=4)
		self.ready=False
		self.config=self._readConfig()
		localLangs=[]
		for localLang in locale.getlocale():
			if "_" in localLang:
				localLangs.append(localLang.split("_")[0])
				localLangs.append(localLang.split("_")[-1].lower())
		localLangs.insert(0,"C")
		self.langs=list(set(localLangs))
		self.plugins=self._loadPlugins()
		self._debug("Supported formats: {}".format(self.supportedformats))
		self._initCore()
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("core: {}".format(msg))
	#def _debug

	def _error(self,e,msg=""):
		print("{}: {}\n<------ TRACEBACK ------>".format(msg,e))
		print(traceback.format_exc())
		print ("<------ TRACEBACK -----/>")
	#def _error

	def setConfigValue(self,key,value):
		self.config.update({key:value})
	#def setConfigValue

	def _readConfig(self):
		config={}
		if os.path.isfile(CONFIG):
			fcontent=""
			with open(CONFIG,"r") as f:
				fcontent=f.read()
			config=json.loads(fcontent)
		return(config)
	#def _readConfig

	def _importPlugin(self,modpath):
		plugin=None
		modname=os.path.basename(modpath).replace(".py","")
		self._debug("Inspecting plugin {} at {}".format(modname,modpath))
		if os.path.exists(modpath):
			try:
				spec = importlib.util.spec_from_file_location("engine",modpath)
				pluginlib = importlib.util.module_from_spec(spec)
				sys.modules["module.name"] = pluginlib
				spec.loader.exec_module(pluginlib)
				pluginmod=pluginlib.engine(self)
				
				#if hasattr(pluginlib,"engine")==True:
				if hasattr(pluginmod,"bundle")==True:
					modname=pluginmod.bundle
					self.supportedformats.append(pluginmod.bundle)
				else:
					modname=modname.replace(".py","")
				plugin={modname:pluginmod}
				#else:
				#	self._debug("Discarded {}".format(modname))
			except Exception as e:
				self._error("Failed importing {0}: {1}".format(modpath,e))
		else:
			self._debug("{} not found".format(modpath))
		print("****")
		return(plugin)
	#def _importPlugin

	def _loadPlugins(self):
		pluginDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"plugins")
		plugins={}
		self._debug("Accessing {}".format(pluginDir))
		if os.path.exists(pluginDir):
			for f in os.scandir(pluginDir):
				plugin=None
				if (not f.name.endswith(".py")) or (f.name.startswith("_")):
					continue
				pluginfo=self._importPlugin(f.path)
				print("PLUGINFO {}".format(pluginfo))
				if pluginfo!=None:
					#plugin=pluginfo.get(f.name.replace(".py",""),"")
					if hasattr(plugin,"enabled")==True:
						if plugin.enabled==False:
							self._debug("Disabled plugin {}".format(f.name))
							continue
					priority=100
					if hasattr(plugin,"priority")==True:
						priority=plugin.priority
					if priority not in plugins.keys():
						plugins[priority]={}
					modkey=list(pluginfo.keys())[0]
					plugindict=plugins[priority]
					if plugindict.get(modkey)!=None:
						plugindict[modkey].append(pluginfo[modkey])
					else:
						plugindict.update({modkey:[pluginfo[modkey]]})
		return(plugins)
	#def _loadPlugins

	def _toFile(self,store,fxml):
		store.to_file(Gio.File.parse_name(fxml),appstream.NodeToXmlFlags.FORMAT_MULTILINE|appstream.NodeToXmlFlags.FORMAT_INDENT)
	#def _toFile

	def _fromFile(self,store,fxml):
		self._debug("Attempt to load {} using {}".format(store,fxml))
		if os.path.exists(fxml):
			try:
				with open(fxml,"r") as f:
					fcontent=f.read()
				fcontent=fcontent.replace("&lt;","").replace("&gt","").replace("&"," &amp;")
				store.from_xml(fcontent)
				self._debug("Added {} apps".format(len(store.get_apps())))
			except Exception as e:
				self._debug("Malformed {}".format(fxml))
				tree = ET.fromstring(fcontent)
				r=tree.getroot()
				for description in r.iter('description'):
					txt=[]
					for i in list(description):
						desc=i.text
						if isinstance(desc,str)==False:
							desc=""
						description.remove(i)
						txt.append(desc.strip())
					text=html.escape("{}".format(txt))
					desc="<p>{}</p>".format(text)
					try:
						elem=ET.fromstring(desc)
					except Exception as e:
						self._error(e,msg="_fromFile")
					description.append(elem)
				os.unlink(fxml)
				tree.write(fxml,xml_declaration="1.0",encoding="UTF-8")
				self._debug("Updated {}".format(fxml))
				try:
					with open(fxml,"r") as f:
						fcontent=f.read()
					store.from_xml(fcontent)
					self._debug("Added {} apps".format(len(store.get_apps())))
				except Exception as e:
					self._error(e,msg="Error fixing. Requires user intervention")
		else:
			self._debug("{} not found".format(fxml))
		return(store)
	#def _fromFile

	def _getVerifiedOrigins(self):
		matchTables=self.config.get("verifiedProvider",[])
		verifiedOrigins=[]
		for matchTable in matchTables:
			for idx,store in self.stores.items():
				if isinstance(idx,int)==False:
					continue
				if store.get_origin()==matchTable:
					verifiedOrigins.append(idx)
		return(verifiedOrigins)
	#def _getVerifiedOrigins

	def _preLoadVerified(self,verifiedOrigins):
		store=appstream.Store()
		for idx in verifiedOrigins:
			for app in self.stores[idx].get_apps():
				mergeApp=self._preMergeApp(app)
				oldApp=store.get_app_by_id(mergeApp.get_id())
				if oldApp!=None:
					store.remove_app(app)
					try:
						mergeApp.subsume(oldApp)#,appstream.AppSubsumeFlags.NO_OVERWRITE)
					except Exception as e:
						self._error(e,msg="_preLoadVerified")
				store.add_app(mergeApp)
		self._debug("Verified table count: {}".format(store.get_size()))
		return(store)
	#def _preLoadVerified

	def _preMergeApp(self,app):
		newId=app.get_id()
		if len(app.get_bundles())>0:
			if app.get_bundles()[0].get_kind()==appstream.BundleKind.FLATPAK:
				newId=app.get_id().replace(".desktop","").split(".")[-1]
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
				newId=newId.lower().replace(".appimage","").split(".")[-1]
			elif app.get_bundles()[0].get_kind()==appstream.BundleKind.SNAP:
				newId=app.get_id().replace(".desktop","").split(".")[-1]
		app.set_id(newId.lower().rstrip(".").lstrip("."))
		return (app)
	#def _preMergeApp
	
	def _mergeApps(self):
		self._debug("Filling work table")
		self.stores["mainB"]=appstream.Store()
		verifiedOrigins=self._getVerifiedOrigins()
		if len(verifiedOrigins)>0:
			self.stores["mainB"]=self._preLoadVerified(verifiedOrigins)
		self.stores["main"].set_add_flags(appstream.StoreAddFlags.USE_MERGE_HEURISTIC)
		self.stores["main"].add_apps(self.stores["mainB"].dup_apps())
		for storeId in self.stores.keys():
			if storeId in verifiedOrigins:
				continue
			self._debug("Process {}".format(storeId))
			if isinstance(storeId,int):
				for app in self.stores[storeId].get_apps():
					mergeApp=self._preMergeApp(app)
					oldApp=self.stores["main"].get_app_by_id(mergeApp.get_id())
					if oldApp!=None:
						try:
							self.stores["main"].remove_app(oldApp)
							mergeApp.subsume(oldApp)#,appstream.AppSubsumeFlags.NO_OVERWRITE)
						except Exception as e:
							self._error(e,msg="_mergeApps")
					oldApp=self.stores["mainB"].get_app_by_id(mergeApp.get_id())
					if oldApp!=None:
						self.stores["mainB"].remove_app(oldApp)
						self.stores["mainB"].add_app(mergeApp)
					self.stores["main"].add_app(mergeApp)
		if self.config.get("onlyVerified",False)==True:
			self.loadToggle()
	#def _mergeApps

	def loadToggle(self):
		tmp=self.stores["main"]
		self.stores["main"]=self.stores["mainB"]
		self.stores["mainB"]=tmp
	#def _loadToggle

	def reload(self):
		fxml=os.path.join(CACHE,"main.xml")
		if os.path.exists(fxml):
			os.unlink(fxml)
		self.stores["main"].remove_all()
		self.stores["mainB"].remove_all()
		for storeId in self.stores.keys():
			self._debug("Process {}".format(storeId))
			if isinstance(storeId,int):
				self.stores[storeId].remove_all()
		self._debug("Reloading rebost core")
		init=self.thExecutor.submit(self._initEngines)
		init.add_done_callback(self._rebostOperative)
	#def reload(self):

	def export(self):
		fxml=os.path.join(CACHE,"main.xml")
		try:
			self._toFile(self.stores["main"],fxml)
		except Exception as e:
			self._error(e,msg="export")
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
		if self.config.get("verifiedProvider","")!="":
			if self.config.get("onlyVerified",False)==True:
				print("\n******************************************************")
				print("************* RESTRICTED MODE ENABLED ****************")
				print("Verified by {}".format(self.config["verifiedProvider"]))
				print("******************************************************\n")
		for priority in priorities:
			print("Priority: {}".format(priority))
			pluginfo=self.plugins[priority]
			print("Priority plugin: {}".format(pluginfo))
			for plugkey,plugmod in pluginfo.items():
				print("Priority item: {}".format(plugmod))
				print("Priority item: {}".format(plugkey))
				if isinstance(plugkey,self.appstream.BundleKind):
					self._debug((priority,plugkey))
					for mod in plugmod:
						init=self.thExecutor.submit(mod.getAppstreamData)
						self.initProc+=1
						init.add_done_callback(self._callBackInit)
	#def _initEngines

	def _loadFromCache(self):
		fxml=os.path.join(CACHE,"main.xml")
		try:
			cacheStore=self._fromFile(self.stores["main"],fxml)
		except Exception as e:
			self._error(e,msg="_loadFromCache")
		if self.ready==False:
			self._debug("Loading {} apps from cache".format(cacheStore.get_size()))
			if cacheStore.get_size()>0:
				self.stores["main"]=cacheStore
				self._debug("Cached store loaded. Rebost will update data now")
				self.ready=True
	#def _loadFromCache

	def getExternalInstaller(self):
		return(self.config.get("externalInstaller",""))
	#def getExternalInstaller

	def _initCore(self):
		self.thExecutor.submit(self._loadFromCache)
		self._initEngines()
	#def _initCore
#class _RebostCore

