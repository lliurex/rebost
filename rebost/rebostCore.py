#!/usr/bin/env python3
import sys
import importlib
import requests
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
		self.dbg=True
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
		self.config={}
		self.procId=1

	def run(self):
		self._log("Starting rebost")
		self._loadPlugins()
		self._loadPluginInfo()
		self._processConfig()
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
		self._debug("Accessing {}".format(self.plugDir))
		disabledPlugins={}
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
						self._log("Failed importing {0}: {1}".format(plugin,e))
						continue
					if "rebostHelper" in plugin:
						enabled=True
					else:
						enabled=self._getPluginEnabled(pluginObject)
					if enabled!=False:
						self.plugins[plugin.replace(".py","")]=pluginObject
						if enabled:
							print("Plugin loaded: {}".format(plugin))
						else:
							print("{} will set its status".format(plugin))
					else:
						self._debug("Plugin disabled: %s"%plugin)
						disabledPlugins[plugin.replace(".py","")]=False
		if len(disabledPlugins)>0:
			self._writeConfig(disabledPlugins)
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
			if len(mandatory)>0:
				#Disable plugin as not all values have been set
				if plugin!="rebostHelper":
					print("Disable {} as faulting values: {}".format(plugin,mandatory))
					delPlugins.append(plugin)
				else:
					pluginObject.setDebugEnabled(self.dbg)
			else:
				self.pluginInfo[plugin]=plugInfo
				if self.propagateDbg:
					try:
						pluginObject.setDebugEnabled(self.dbg)
					except Exception as e:
						print(e)
		for plugin in delPlugins:
			del(self.plugins[plugin])
	#def _loadPluginInfo

	def _writeConfig(self,config):
		cfg=self._readConfig()
		cfgFile="/usr/share/rebost/store.json"
		for key,value in config.items():
			key=key.replace("Helper","")
			cfg[key]=value
		if os.path.isfile(cfgFile):
			with open(cfgFile,'w') as f:
				try:
					f.write(json.dumps(cfg,skipkeys=True))
				except:
					pass
	#def _writeConfig

	def _processConfig(self):
		cfg=self._readConfig()
		sw_pkg=False
		if "enabled" not in cfg.keys():
			cfg["packageKit"]=True
			cfg["enabled"]=True
			self._writeConfig(cfg)
		for key,value in cfg.items():
			if value=="enabled":
				continue
			if value==True:
				self._enable(key)
				if key.lower() in ["apt","package","packagekit"]:
					self._enable("appstream")
			else:
				delPlugin=key
				if key=="snap":
					delPlugin="snapHelper"
				elif key=="flatpak":
					delPlugin="flatpakHelper"
				elif key.lower() in ["apt","package","packagekit"]:
					delPlugin="packageKit"
					#if "appstreamHelper" in self.pluginInfo.keys():
					#	del(self.pluginInfo["appstreamHelper"])
					#	self._disable("appstream")
				elif key=="appimage":
					delPlugin="appimageHelper"
				if delPlugin in self.pluginInfo.keys():
					del(self.pluginInfo[delPlugin])
				self._disable(key)
	#def _processConfig

	def _readConfig(self):
		cfgFile="/usr/share/rebost/store.json"
		cfg={}
		if os.path.isfile(cfgFile):
			with open(cfgFile,'r') as f:
				try:
					cfg=json.loads(f.read())
				except:
					pass
		return(cfg)
	#def _readConfig

	def _enable(self,bundle):
		swEnabled=False
		tmpPath="/usr/share/rebost/tmp"
		if os.path.isdir(tmpPath):
			prefix=""
			if bundle=="apt" or bundle=="package":
				prefix="pk"
			elif bundle=="snap":
				prefix="sn"
			elif bundle=="flatpak":
				prefix="fp"
			elif bundle=="appimage":
				prefix="ai"
			elif bundle=="appstream":
				prefix="ai"
			if prefix:
				for f in os.listdir(tmpPath):
					if f.startswith(prefix):
						swEnabled=True
						break
		if swEnabled==False:
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
			if bundle=="apt" or bundle=="packageKit":
				prefix="pk"
			elif bundle=="snap":
				prefix="sn"
			elif bundle=="flatpak":
				prefix="fp"
			elif bundle=="appimage":
				prefix="ai"
			elif bundle=="appstream":
				prefix="as"
			if prefix:
				for f in os.listdir(tmpPath):
					if f.startswith(prefix):
						os.remove(os.path.join(tmpPath,f))
						swRemoved=True
		if swRemoved==True:
			if os.path.isfile(os.path.join(tmpPath,"sq.lu")):
				os.remove(os.path.join(tmpPath,"sq.lu"))
	#def _disable

	def _chkNetwork(self):
		try:
			requests.get('https://portal.edu.gva.es/',timeout=1)
			return True
		except:
			return False
	#def _chkNetwork

	def _autostartActions(self):
		actionDict={}
		postactionDict={}
		postactions=[]
		actions=[]
		for plugin,info in self.pluginInfo.items():
			actions=info.get('autostartActions',[])
			postactions=info.get('postAutostartActions',[])
			if len(actions)>0:
				self._debug("Loading autostart actions for {}".format(plugin))
				priority=info.get('priority',0)
				newDict=actionDict.get(priority,{})
				newDict[plugin]=actions
				network=self._chkNetwork()
				if network==True or priority==100:
					actionDict[priority]=newDict.copy()
				else:
					print("Error autostart {}: Network error".format(plugin))
					actionDict[priority]=newDict.copy()
			if len(postactions)>0:
				priority=info.get('priority',0)
				newDictPost=actionDict.get(priority,{})
				newDictPost[plugin]=postactions
				postactionDict[priority]=newDictPost.copy()
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
						self._log("Error launching {} from {}: {}".format(action,plugin,e))
						print("Error launching {} from {}: {}".format(action,plugin,e))
		for proc in procList:
			if isinstance(proc,threading.Thread):
				proc.join()
			elif isinstance(proc,multiprocessing.Process):
				proc.join()
		self._debug("postactions: {}".format(postactionDict))
		if len(postactionDict)>0:
			actionList=list(postactionDict.keys())
			actionList.sort(reverse=False)
			procList=[]
			for priority in actionList:
				self._debug("Launching postactions")
				for plugin,actions in postactionDict[priority].items():
					for action in actions:
						try:
							pr=self._execute(action,'','',plugin=plugin,th=True)
							pr.join()
						except Exception as e:
							self._debug("Error launching {} from {}: {}".format(action,plugin,e))
	#def _autostartActions
	
	def execute(self,action,package='',extraParms=None,extraParms2=None,user='',n4dkey='',**kwargs):
		rebostPkgList=[]
		store=[]
		self._debug("Parms:\n-action: {}*\n-package: {}*\n-extraParms: {}*\nplugin: {}*".format(action,package,extraParms,extraParms2))
		if extraParms:
			for regPlugin,info in self.pluginInfo.items():
				if info.get('packagekind','package')==str(extraParms):
					bundle=str(extraParms)
		plugin=''
		for plugName,plugAction in self.pluginInfo.items():
			if action in plugAction.get('actions',[]):
				plugin=plugName
				break
		coreAction=False
		if len(plugin)==0:
			#search for a local method
			if hasattr(self,action):
				plugin="core"
				rebostPkgList.extend(self._executeCoreAction(action))
		if plugin!="core":
			self._debug("Executing {} from {}".format(action,self.plugins[plugin]))
			self._debug("Parms:\n-action: {}%\n-package: {}%\n-extraParms: {}%\nplugin: {}%\nuser: {}%".format(action,package,extraParms,plugin,user))
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
				try:
					appJson=json.loads(app)
					if appJson.get('name').startswith("lliurex-meta")==False:
						store.append(app)
				except:
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

	def _executeCoreAction(self,action,th=True):
		retval=1
		rs=[{}]
		proc=None
		self._debug("Launching {} from CORE (th {})".format(action,th))
		func=eval("self.{}".format(action))
		if th:
			proc=threading.Thread(target=func)
		else:
			proc=multiprocessing.Process(target=func,daemon=False)
		try:
			proc.start()
		except Exception as e:
			print(e)
			retval=0
		return(rs)
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

	def getFiltersEnabled(self):
		state=True
		try:
			state=self.plugins["sqlHelper"].whitelist
		except Exception as e:
			print(e)
			print("Critical error. Restarting rebost service now")
			self.run()
		return(state)

	def getProgress(self):
		rs=self.plugins['rebostPrcMan'].execute(action='progress')
		return(json.dumps(rs))
	#def getProgress(self):

	def forceUpdate(self,force=False):
		self._debug("Rebost forcing update...")
		rebostPath="/usr/share/rebost/"
		rebostTmpPath="/usr/share/rebost/tmp"
		self._debug("Cleaning tmp")
		for i in os.scandir(rebostTmpPath):
			try:
				os.remove(i.path)
			except Exception as e:
				print(e)
				self._debug(e)
		if force==True:
			self._debug("Removing databases")
			for i in os.scandir(rebostPath):
				if i.path.endswith(".db"):
					try:
						os.remove(i.path)
					except Exception as e:
						print(e)
						self._debug(e)
		return(self.restart())
	#def getProgress(self):

	def restart(self):
		self.run()
		return('[{}]')


	def update(self):
		return
	
	def fullUpdate(self):
		return

