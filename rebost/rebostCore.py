#!/usr/bin/env python3
import sys
import importlib
import os,shutil
import multiprocessing
import threading
import time
import json
import signal
import subprocess
import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream

class Rebost():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.plugins=""
		self.gui=False
		self.propagateDbg=True
		self.cache="/tmp/.cache/rebost"
		self.cacheData=os.path.join("{}".format(self.cache),"xml")
		self.plugDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"plugins")
		self.plugins={}
		self.pluginInfo={}
		self.plugAttrMandatory=["enabled","packagekind","priority","actions"]
		self.plugAttrOptional=["user","autostartActions","postAutostartActions"]
		self.process={}
		self.store=appstream.Store()
		self._loadPlugins()
		self._loadPluginInfo()
		if self.propagateDbg:
			self._setPluginDbg()
		self.cofig={}
		self.procId=1

	def run(self):
		self._readConfig()
		self._log("Starting rebost")
		self._autostartActions()
		self._log("Autostart ended. Populating data")
	#def run

	def _log(self,msg):
		print("rebost: {}".format(msg))
		try:
			with open("/var/log/rebost.log","a") as f:
				f.write("{}\n".format(msg))
		except:
			pass
	#def _log

	def _debug(self,msg):
		if self.dbg:
			print("rebost: {}".format(msg))
	#def _debug
	
	def _setGuiEnabled(self,state):
		self._debug("Set gui mode: {}".format(state))
		self.gui=state

	def _setPluginDbg(self):
		for plugin,pluginObject in self.plugins.items():
			try:
				pluginObject.setDebugEnabled(self.dbg)
			except Exception as e:
				print(e)
	#def _setPluginDbg

	####
	#Load and register the plugins from plugin dir
	####
	def _loadPlugins(self):
		self._debug("Accessing %s"%self.plugDir)
		if os.path.isdir(self.plugDir):
			sys.path.insert(1,self.plugDir)
			for plugin in os.listdir(self.plugDir):
				if plugin.endswith(".py") and plugin!='__init__.py':
					try:
						imp=importlib.import_module((plugin.replace(".py","")))
						#Get plugin status
						if "rebostHelper" not in plugin:
							pluginObject=imp.main()
						else:
							pluginObject=imp
					except Exception as e:
						self._log("Failed importing %s: %s"%(plugin,e))
						continue
					if "rebostHelper" in plugin:
						enabled=True
					else:
						enabled=self._getPluginEnabled(pluginObject)
					if enabled!=False:
						self.plugins[plugin.replace(".py","")]=pluginObject
						if enabled:
							self._debug("Plugin loaded: %s"%plugin)
						else:
							self._debug("%s will set its status"%plugin)
					else:
						self._debug("Plugin disabled: %s"%plugin)
	#def _loadPlugins

	def _getPluginEnabled(self,pluginObject):
		enabled=None
		if 'enabled' in pluginObject.__dict__.keys():
			enabled=pluginObject.enabled
		return enabled
	#def _getPluginEnabled

	def _loadPluginInfo(self):
		delPlugins=[]
		for plugin,pluginObject in self.plugins.items():
			mandatory=self.plugAttrMandatory.copy()
			plugInfo={}
			for item,value in pluginObject.__dict__.items():
				if item in mandatory or item in self.plugAttrOptional:
					plugInfo["{}".format(item)]=value
					if item=="user":
						pluginObject.__dict__[item]="lliurex"
				if item in mandatory:
					mandatory.remove(item)
			if mandatory:
				#Disable plugin as not all values have been set
				if plugin!="rebostHelper":
					self._debug("Disable {} as faulting values: {}".format(plugin,mandatory))
					delPlugins.append(plugin)
			else:
				self.pluginInfo[plugin]=plugInfo
		for plugin in delPlugins:
			del(self.plugins[plugin])
	#def _loadPluginInfo

	def _readConfig(self):
		cfgFile="/usr/share/rebost/store.json"
		if os.path.isfile(cfgFile):
			with open(cfgFile,'r') as f:
				cfg=json.loads(f.read())
			for key,value in cfg.items():
				if value==True:
					self._enable(key)
				else:
					if key=="snap":
						del(self.pluginInfo["snapHelper"])
					elif key=="flatpak":
						del(self.pluginInfo["flatpakHelper"])
					elif key=="apt":
						del(self.pluginInfo["packageKit"])
					elif key=="appimage":
						del(self.pluginInfo["appimageHelper"])
					self._disable(key)
	#def _readConfig

	def _enable(self,bundle):
		swEnabled=True
		tmpPath="/usr/share/rebost/tmp"
		if os.path.isdir(tmpPath):
			prefix=""
			if bundle=="apt":
				prefix="pk"
				prefix2="as"
			elif bundle=="snap":
				prefix="sn"
				prefix2="sn"
			elif bundle=="flatpak":
				prefix="fp"
				prefix2="fp"
			elif bundle=="appimage":
				prefix="ai"
				prefix2="ai"
			if prefix:
				for f in os.listdir(tmpPath):
					if f.startswith(prefix) or f.startswith(prefix2):
						swEnabled=False
						break
		if swEnabled==True:
			if os.path.isfile(os.path.join(tmpPath,"sq.lu")):
				os.remove(os.path.join(tmpPath,"sq.lu"))
	#def _enable

	def _disable(self,bundle):
		tmpPath="/usr/share/rebost/tmp"
		dbPath=os.path.join("/usr/share/rebost","{}.db".format(bundle.lower()))
		if os.path.isfile(dbPath):
			os.remove(dbPath)
		swRemoved=False
		if os.path.isdir(tmpPath):
			prefix=""
			if bundle=="apt":
				prefix="pk"
				prefix2="as"
			elif bundle=="snap":
				prefix="sn"
				prefix2="sn"
			elif bundle=="flatpak":
				prefix="fp"
				prefix2="fp"
			elif bundle=="appimage":
				prefix="ai"
				prefix2="ai"
			if prefix:
				for f in os.listdir(tmpPath):
					if f.startswith(prefix) or f.startswith(prefix2):
						os.remove(os.path.join(tmpPath,f))
						swRemoved=True
		if swRemoved==True:
			if os.path.isfile(os.path.join(tmpPath,"sq.lu")):
				os.remove(os.path.join(tmpPath,"sq.lu"))
	#def _disable

	def _autostartActions(self):
		actionDict={}
		postactionDict={}
		postactions=''
		actions=''
		for plugin,info in self.pluginInfo.items():
			actions=info.get('autostartActions',[])
			postactions=info.get('postAutostartActions',[])
			if actions:
				self._debug("Loading autostart actions for {}".format(plugin))
				priority=info.get('priority',0)
				newDict=actionDict.get(priority,{})
				newDict[plugin]=actions
				actionDict[priority]=newDict.copy()
			if postactions:
				postactionDict[plugin]=postactions
		#Launch actions by priority
		actionList=list(actionDict.keys())
		actionList.sort(reverse=False)
		procList=[]
		for priority in actionList:
			for plugin,actions in actionDict[priority].items():
					for action in actions:
						try:
							procList.append(self._execute(action,'','',plugin=plugin,th=False))
						except Exception as e:
							self._debug("Error launching {} from {}: {}".format(action,plugin,e))
		for proc in procList:
			if isinstance(proc,threading.Thread):
				proc.join()
			elif isinstance(proc,multiprocessing.Process):
				proc.join()
		self._debug("postactions: {}".format(postactions))
		if postactionDict:
			self._debug("Launching postactions")
			for plugin,actions in postactionDict.items():
				for action in actions:
					try:
						self._execute(action,'','',plugin=plugin,th=True)
					except Exception as e:
						self._debug("Error launching {} from {}: {}".format(action,plugin,e))
	#def _autostartActions
	
	def execute(self,action,package='',extraParms=None,extraParms2=None,user='',n4dkey='',**kwargs):
		rebostPkgList=[]
		store=[]
		self._debug("Parms:\n-action: {}\n-package: {}\n-extraParms: {}\nplugin: {}".format(action,package,extraParms,extraParms2))
		if extraParms:
			for regPlugin,info in self.pluginInfo.items():
				if info.get('packagekind','package')==str(extraParms):
					bundle=str(extraParms)
		plugin='sqlHelper'
		for plugName,plugAction in self.pluginInfo.items():
			if action in plugAction.get('actions',[]):
				plugin=plugName
				break

		if rebostPkgList==[]:
			#sqlHelper now manages all operations but load
			self._debug("Executing {} from {}".format(action,self.plugins[plugin]))
			self._debug("Parms:\n-action: {}\n-package: {}\n-extraParms: {}\nplugin: {}\nuser: {}".format(action,package,extraParms,plugin,user))
			rebostPkgList.extend(self.plugins[plugin].execute(action=action,parms=package,extraParms=extraParms,extraParms2=extraParms2,user=user,n4dkey=n4dkey,**kwargs))
		#Generate the store with results and sanitize them
		if action!='getCategories':
			if not isinstance(rebostPkgList,list):
				rebostPkgList=[rebostPkgList]
			store=self._sanitizeStore(rebostPkgList)
		else:
			catList=[]
			for cat in rebostPkgList:
				catList.append(cat[0])
			store=json.dumps(catList)
		return(store)
	#def execute
			
	def _sanitizeStore(self,appstore):
		self._debug("Sanitize store {}".format(int(time.time())))
		store=[]
		unorder_store=[]
		pkgDict={}
		components=[]
		self._debug("Begin Sanitize store {}".format(int(time.time())))
		for rebostpkg in appstore:
			if isinstance(rebostpkg,tuple):
				try:
					(pkg,app)=rebostpkg
				except:
					self._debug("Error sanitize")
					self._debug(rebostpkg)
					continue
			else:
				app=rebostpkg
			if isinstance(app,str):
				appJson=json.loads(app)
				if appJson.get('name').startswith("lliurex-meta")==False:
					store.append(app)
			else:
				store.append(app)
		self._debug("End sanitize")
		return((json.dumps(store)))
	#def _sanitizeStore
	
	def _execute(self,action,package,bundle='',plugin=None,th=True):
		#action,args=action_args.split("#")
		proc=None
		plugList=[]
		if not plugin:  
			for plugin,info in self.pluginInfo.items():
				if action in info['actions']:
					if bundle:
						if ((bundle==info['packagekind']) or (info['packagekind'] in ['*',''])):
							plugList.append(plugin)
					else:
						plugList.append(plugin)
		else:
			plugList.append(plugin)
		if plugList:
			for plugin in plugList:
				proc=self._executeAction(plugin,action,package,bundle,th)
		else:
			proc=None
		return(proc)
	#def _execute

	def _executeAction(self,plugin,action,package,bundle='',th=True):
		retval=1
		proc=None
		self._debug("Launching {} from {} (th {})".format(action,plugin,th))
		if th:
			proc=threading.Thread(target=self.plugins[plugin].execute,kwargs=({'action':action,'parms':package}))
		else:
			proc=multiprocessing.Process(target=self.plugins[plugin].execute,kwargs=({'action':action,'parms':package}),daemon=False)
		try:
			proc.start()
		except Exception as e:
			print(e)
			retval=0
		return(proc)
	#def _executeAction
	
	def getEpiPkgStatus(self,epifile):
		self._debug("Getting status from {}".format(epifile))
		stdout='1'
		if os.path.isfile(epifile):
			proc=subprocess.run(["{}".format(epifile),'getStatus'],stdout=subprocess.PIPE)
			stdout=proc.stdout.decode().strip()
		else:
			stdout="23"
		return (stdout)
	#def getEpiPkgStatus

	def getProgress(self):
		rs=self.plugins['rebostPrcMan'].execute(action='progress')
		return(json.dumps(rs))
	#def getProgress(self):

	def forceUpdate(self,force=False):
		self._debug("Rebost forcing update...")
		rebostPath="/usr/share/rebost/"
		rebostTmpPath="/usr/share/rebost/tmp"
		for i in os.listdir(rebostTmpPath):
			try:
				os.remove(os.path.join(rebostTmpPath,i))
			except Exception as e:
				print(e)
				self._debug(e)
		return()
	#def getProgress(self):

	def update(self):
		return
	
	def fullUpdate(self):
		return

