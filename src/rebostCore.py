#!/usr/bin/env python3
import sys
import importlib
import requests
import os,shutil,stat
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
		self.propagateDbg=True
		self.dbCache="/tmp/.cache/rebost"
		self.rebostWrkDir=os.path.join(self.dbCache,os.environ.get("USER"))
		self._iniCache()
		self.confFile=os.path.join(self.rebostPath,"store.json")
		if os.path.exists(self.confFile)==False:
			if os.path.exists(self.rebostPath)==False:
				os.makedirs(self.rebostPath)
			shutil.copy2("/usr/share/rebost/store.json",self.confFile)
		self.includeFile=os.path.join(self.rebostPath,"lists.d")
		self.rebostPathTmp=os.path.join(self.rebostWrkDir,"tmp")
		self.plugDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"plugins")
		self.plugins={}
		self.pluginInfo={}
		self.plugAttrMandatory=["enabled","packagekind","priority","actions"]
		self.plugAttrOptional=["user","autostartActions","postAutostartActions"]
		self.process={}
		self.store=appstream.Store()
		self.config={}
		self.procId=1
		signal.signal(signal.SIGALRM,self._launchRebostUpdated)
	#def __init__(self,*args,**kwargs):

	def _iniCache(self):
		if os.path.exists(self.rebostWrkDir)==True:
			for f in os.scandir(self.rebostWrkDir):
				if os.path.isfile(f.path):
					if f.path.endswith(".db"):
						os.unlink(f.path)
				elif os.path.isdir(f.path):
					for fd in os.scandir(f.path):
						if os.path.isfile(fd.path):
							os.unlink(fd.path)
			#shutil.rmtree(self.rebostWrkDir)
		else:
			os.makedirs(self.rebostWrkDir)
		try:
			os.chmod(self.dbCache,stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)
		except:
			pass
		finally:
			os.chmod(self.rebostWrkDir,stat.S_IRWXU)
		home=os.environ.get("HOME",self.dbCache)
		if len(home)>0:
			self.cache=os.path.join(home,".cache","rebost")
		else:
			self.cache=self.rebostWrkDir
		self.rebostPath=os.path.join(home,".config","rebost")
	#def _iniCache
	
	def _launchRebostUpdated(self,*args,**kwargs):
		self._copyTmpToCache()
		self._log("Cache restored")
		signal.raise_signal(signal.SIGUSR2)
	#def _launchRebostUpdated(self,*args,**kwargs):

	def run(self):
		self._log("Starting rebost")
		self._loadPlugins()
		self._log("Plugins loaded")
		self._loadPluginInfo()
		self._log("Plugins processed")
		self._processConfig()
		self._log("Config readed")
		if self._copyCacheToTmp()==True:
			self._log("Cache enabled")
			self._beginAutostartActions()
		else:
			self._log("Cache unavailable")
			self._autostartActions()
		self._log("Autostart ended.")
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
						self._debug("Plugin disabled: {}".format(plugin))
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
		return()
		cfg=self._readConfig()
		cfgFile=self.confFile
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
		for plugin,state in cfg.items():
			if state==True:
				self._enable(plugin)
			else:
				self._disable(plugin)
		self.restricted=cfg.get("restricted",True)
		self.mainTableForRestrict=cfg.get("maintable","")
		self.forceApps=cfg.get("forceApps",{})
	#def _processConfig

	def _readConfig(self):
		cfg={}
		include={}
		if os.path.isfile(self.confFile):
			with open(self.confFile,'r') as f:
				try:
					cfg=json.loads(f.read())
				except:
					pass
		if os.path.isfile(self.includeFile):
			with open(self.includeFile,'r') as f:
				try:
					include=json.loads(f.read())
				except:
					pass
		if len(include)>0:
			cfg["forceApps"]=include
		return(cfg)
	#def _readConfig

	def _enable(self,bundle):
		swEnabled=False
		tmpPath="/usr/share/rebost/tmp"
		if os.path.isdir(tmpPath) and len(bundle)>=4:
			prefix=bundle[0]+bundle[3]
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
		disable=[]
		for plugin,data in self.pluginInfo.items():
			if data.get("packagekind","")==bundle:
				disable.append(plugin)
		tables={"eduapp":"eduapps.db","zomando":"zomandos.db","package":"packagekit.db","flatpak":"flatpak.db","snap":"snap.db","appimage":"appimage.db"}
		for plugin in disable:
			self._debug("Config disable {}".format(plugin))
			del(self.pluginInfo[plugin])
			table=tables.get(bundle,"")
			if len(table)>0:
				self._debug("Deleting table {}".format(table))
				tpath=os.path.join(self.rebostPathTmp,table)
				if os.path.isfile(tpath):
					os.remove(tpath)
				prefix=plugin[0]+plugin[3]
				fprefix=os.path.join(self.rebostPathTmp,"{}.lu".format(prefix.lower()))
				if os.path.isfile(fprefix):
					os.remove(fprefix)
		if len(disable)>0:
			if os.path.isfile(os.path.join(self.rebostPathTmp,"sq.lu")):
				os.remove(os.path.join(self.rebostPathTmp,"sq.lu"))
		return()
	#def _disable

	def _chkNetwork(self):
		def trace_function(frame, event, arg):
			if time.time() - start > TOTAL_TIMEOUT:
				raise Exception('Timed out!') # Use whatever exception you consider appropriate.

			return trace_function
		##
		TOTAL_TIMEOUT = 1
		start = time.time()
		sys.settrace(trace_function)

		sw=True
		try:
			res = requests.get('http://lliurex.net/jammy/', timeout=(1, 2)) # Use whatever timeout values you consider appropriate.
		except:
			sw=False
		finally:
			sys.settrace(None) # Remove the time constraint and continue normally.
		return sw
	#def _chkNetwork

	def _copyCacheToTmp(self):
		copied=False
		tmpCache=os.path.join(self.cache,"tmp")
		if os.path.exists(tmpCache):
			if os.path.exists(os.path.join(self.rebostPathTmp,"sq.lu"))==True:
				return()
			elif os.path.exists(self.rebostPathTmp)==False:
				os.makedirs(self.rebostPathTmp)
			for db in os.scandir(self.cache):
				if db.path.endswith(".db"):
					shutil.copy2(db.path,os.path.join(self.rebostWrkDir,db.name))
					if copied==False:
						copied=True
					self._debug("Copy: {0} -> {1}".format(db.path,os.path.join(self.rebostWrkDir,db.name)))
			for lu in os.scandir(tmpCache):
				if lu.path.endswith(".lu"):
					shutil.copy2(lu.path,os.path.join(self.rebostPathTmp,lu.name))
					self._debug("Copy: {0} -> {1}".format(lu.path,os.path.join(self.rebostWrkDir,lu.name)))
		return(copied)
	#def _copyCacheToTmp

	def _copyTmpToCache(self):
		if os.path.exists(self.cache)==False:
			os.makedirs(self.cache)
		if os.path.exists(self.rebostPathTmp):
			for db in os.scandir(self.rebostWrkDir):
				if db.path.endswith(".db"):
					shutil.copy2(db.path,"{}/{}".format(self.cache,db.name))
			tmpCache=os.path.join(self.cache,"tmp")
			if os.path.exists(tmpCache)==False:
				os.makedirs(tmpCache)
			for lu in os.scandir(self.rebostPathTmp):
				if lu.path.endswith(".lu"):
					shutil.copy2(lu.path,os.path.join(tmpCache,lu.name))
					self._debug("Save: {0} -> {1}".format(lu.path,os.path.join(tmpCache,lu.name)))
	#def _copyTmpToCache

	def _beginAutostartActions(self):
		proc=multiprocessing.Process(target=self._autostartActions,daemon=False)
		proc.start()
	#def _beginAutostartActions
		
	def _autostartActions(self):
		actionDict={}
		postactionDict={}
		postactions=[]
		actions=[]
		for plugin,info in self.pluginInfo.items():
			actions=info.get('autostartActions',[])
			packagekind=info.get("packagekind","*")
			if self.forceApps.get(packagekind,{})!={}:
				if hasattr(self.plugins[plugin],"forceApps"):
					self.plugins[plugin].forceApps=self.forceApps[packagekind]
				
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
					#actionDict[priority]=newDict.copy()
			if len(postactions)>0:
				priority=info.get('priority',0)
				newDictPost=postactionDict.get(priority,{})
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
		self._launchRebostUpdated()
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
		if os.path.exists(self.rebostPathTmp)==False:
			self.restart()
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
		#if action=="install" or action=="remove" or action=="test":
		if action=="install" or action=="remove":
			self._launchRebostUpdated()
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
		return(json.dumps(store))
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
	#def _executeCoreAction
	
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
	#def getFiltersEnabled(self):

	def getProgress(self):
		rs=self.plugins['rebostPrcMan'].execute(action='progress')
		return(json.dumps(rs))
	#def getProgress(self):

	def _cleanData(self,force=False):
		self._debug("Cleaning tmp")
		datadirs=[self.rebostPathTmp,os.path.join(self.cache,"tmp")]
		for d in datadirs:
			if os.path.isdir(d)==False:
				continue
			for i in os.scandir(d):
				try:
					os.remove(i.path)
					self._debug("rm {}".format(i.path))
				except Exception as e:
					print(e)
					self._debug(e)
		if force==True:
			self._debug("Removing databases")
			dbDirs=[self.rebostPath,self.cache,self.rebostWrkDir]
			for dbDir in dbDirs:
				for i in os.scandir(dbDir):
					if i.path.endswith(".db"):
						try:
							os.remove(i.path)
							self._debug("rm {}".format(i.path))
						except Exception as e:
							print(e)
							self._debug(e)
	#def _cleanData

	def forceUpdate(self,force=False):
		if isinstance(force,int):
			if force==1:
				force=True
			else:
				force=False
		self._debug("Rebost forcing update. Deep clean: {}".format(force))
		self._cleanData(force=force)
		return(self.restart())
	#def getProgress(self):

	def restart(self):
		self.run()
		return('[{}]')


	def update(self):
		return
	
	def fullUpdate(self):
		return

