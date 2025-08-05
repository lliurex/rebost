#!/usr/bin/python3
import sys,os,time
import traceback
import json
import importlib
import xml
import yaml
import dbus
import locale
import concurrent.futures as Futures
import threading
import gi
from gi.repository import Gio
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream

DBG=True
SCHEMES=os.path.join(os.path.dirname(os.path.realpath(__file__)),"schemes")
WRKDIR=os.path.join(os.environ["HOME"],".local","share","rebost")
DBDIR=os.path.join(WRKDIR,"data")
CACHEDB=os.path.join(os.environ["HOME"],".cache","rebost")


class _RebostCore():
	def __init__(self,*args,**kwargs):
		self.dbg=DBG
		self.SCHEMES=SCHEMES
		self.WRKDIR=WRKDIR
		self.DBDIR=DBDIR
		self.CACHEDB=CACHEDB
		self.DBG=DBG
		self.appstream=appstream
		self.stores={}
		self.initProc=0
		self.store=appstream.Store()
		self.stores={"main":self.store}
		self.supportedformats=[]
		self.thExecutor=Futures.ThreadPoolExecutor(max_workers=4)
		self.ready=False
		self.config={}
		localLangs=[locale.getlocale()[0].split("_")[0]]
		localLangs.append("qcv") #Many years ago in a surrealistic universe someone believed that this was a good idea
		if localLangs[0]=="ca":
			localLangs.append("es")
		elif localLangs[0]=="es":
			localLangs.append("ca")
		localLangs.append("en")
		localLangs.append("C")
		self.langs=list(set(localLangs))
		self.plugins=self._loadPlugins()
		self._debug("Supported formats: {}".format(self.supportedformats))
		self._initCore()
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("core: {}".format(msg))
	#def _debug

	def _importPlugin(self,modname):
		plugin=None
		self._debug("Inspecting plugin {}".format(modname))
		if os.path.exists("plugins/{}".format(modname)):
			try:
				pluginlib=importlib.import_module("plugins.{}".format(modname.replace(".py","")))
				pluginmod=pluginlib.engine(self)
				if hasattr(pluginlib,"engine")==True:
					if hasattr(pluginmod,"bundle")==True:
						modname=pluginmod.bundle
						self.supportedformats.append(pluginmod.bundle)
					else:
						modname=modname.replace(".py","")
					plugin={modname:pluginmod}
				else:
					self._debug("Discarded {}".format(modname))
			except Exception as e:
				self._debug("Failed importing {0}: {1}".format(modname,e))
				print(traceback.format_exc())
		else:
			self._debug("{} not found".format(modname))
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
				pluginfo=self._importPlugin(f.name)
				if pluginfo!=None:
					plugin=pluginfo.get(f.name.replace(".py",""),"")
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

	def _chkTables(self):
		self._debug("Checking tables...")	
		self.plugins[100]["sqlengine"][0].chkDatabases()
	#def _chkTables

	def _toFile(self,store,fxml):
		store.to_file(Gio.File.parse_name(fxml),appstream.NodeToXmlFlags.FORMAT_MULTILINE|appstream.NodeToXmlFlags.FORMAT_INDENT)
	#def _toFile

	def _fromFile(self,store,fxml):
		self._debug("Attempt to load {} using {}".format(store,fxml))
		if os.path.exists(fxml):
			try:
				with open(fxml,"r") as f:
					fcontent=f.read()
				#store.from_file(Gio.File.parse_name(fxml))
				store.from_xml(fcontent)
				self._debug("Added {} apps".format(len(store.get_apps())))
			except Exception as e:
				self._debug("Malformed {}".format(fxml))
				print(e)
		return(store)
	#def _fromFile

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
			elif app.get_bundles()[0].get_kind()==appstream.BundleKind.SNAP:
				newId=app.get_id().replace(".desktop","").split(".")[-1]
		app.set_id(newId.lower().rstrip(".").lstrip("."))
		return (app)
	#def _preMergeApp

	def _mergeApps(self):
		self._debug("Filling work table")
		if self.config.get("restrictTable","")!="":
			self.stores["main"]=self.stores["restricted"]
		try:
			for storeId in self.stores.keys():
				print("Process {}".format(storeId))
				if isinstance(storeId,int):
					for app in self.stores[storeId].get_apps():
						mergeApp=self._preMergeApp(app)
						oldApp=self.stores["main"].get_app_by_id(mergeApp.get_id())
						if oldApp!=None:
							self.stores["main"].remove_app(app)
							mergeApp.subsume_full(oldApp,appstream.AppSubsumeFlags.NO_OVERWRITE)
						self.stores["main"].add_app(mergeApp)
		except Exception as e:
			print(e)
			print(traceback.format_exc())
		fxml=os.path.join(CACHEDB,"main.xml")
		try:
			self._toFile(self.stores["main"],fxml)
		except Exception as e:
			print(e)
		self._debug("Work table ready. Fast mode enabled")
		self.ready=True
	#def _mergeApps

	def _callBackInit(self,*args,**kwargs):
		self._debug("Callback for {}".format(*args))
		storeId=len(self.stores)
		resultSet=args[0]
		self._debug("State {}".format(resultSet.done()))
		if resultSet.done():
			store=resultSet.result()
			self.stores.update({storeId:store})
		self.initProc-=1
		partial=0
		for k in self.stores.keys():
			if isinstance(k,int):
				partial+=len(self.stores[k].get_apps())
		self._debug("Apps in store: {} Init({})".format(partial,self.initProc))
		if self.initProc==0:
			self.thExecutor.submit(self._mergeApps)
	#def _callBackInit(self,*args,**kwargs):

	def _initEngines(self):
		priorities=list(self.plugins.keys())
		priorities.sort()
		for priority in priorities:
			pluginfo=self.plugins[priority]
			for plugkey,plugmod in pluginfo.items():
				if isinstance(plugkey,self.appstream.BundleKind):
					self._debug((priority,plugkey))
					for mod in plugmod:
						init=self.thExecutor.submit(mod.getAppstreamData)
						self.initProc+=1
						init.add_done_callback(self._callBackInit)
	#def _initEngines

	def _initCore(self):
		#self._chkTables()
		self._initEngines()
	#def _initCore
#class _RebostCore

