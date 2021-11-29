#!/usr/bin/env python3
import sys
import importlib
import os
import multiprocessing
import threading
import time
import json
import signal
import logging
import subprocess
import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream

class Rebost():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		logging.basicConfig(format='%(message)s')
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
		#self._loadAppstream()
		self.procId=1

	def run(self):
		self._autostartActions()
	#def run

	def _debug(self,msg):
		if self.dbg:
			logging.warning("rebost: %s"%str(msg))
	#def _debug
	
	def _setGuiEnabled(self,state):
		self._debug("Gui mode: {}".format(state))
		self.gui=state

	def _setPluginDbg(self):
		for plugin,pluginObject in self.plugins.items():
			try:
				if plugin!="rebostHelper":
					pluginObject.setDebugEnabled()
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
						self._debug("Failed importing %s: %s"%(plugin,e))
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

	def _getPluginEnabled(self,pluginObject):
		enabled=None
		if 'enabled' in pluginObject.__dict__.keys():
			enabled=pluginObject.enabled
		return enabled

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
							procList.append(self._execute(action,'','',plugin=plugin,th=True))
						except Exception as e:
							self._debug("Error launching {} from {}: {}".format(action,plugin,e))
		for proc in procList:
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
	
	def execute(self,action,package='',extraParms=None,extraParms2=None,user='',n4dkey=''):
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
			rebostPkgList.extend(self.plugins[plugin].execute(action=action,parms=package,extraParms=extraParms,extraParms2=extraParms2,user=user,n4dkey=n4dkey))
		#Generate the store with results and sanitize them
		if not isinstance(rebostPkgList,list):
			rebostPkgList=[rebostPkgList]
		store=self._sanitizeStore(rebostPkgList,package)
		return(store)
	#def execute
			
	def _sanitizeStore(self,appstore,package=None):
		self._debug("Sanitize store {}".format(int(time.time())))
		store=[]
		unorder_store=[]
		pkgDict={}
		components=[]
		self._debug("Begin Sanitize store {}".format(int(time.time())))
		for rebostpkg in appstore:
			if isinstance(rebostpkg,tuple):
				(pkg,app)=rebostpkg
				store.append(app)
			else:
				store.append(rebostpkg)
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

	def _executeAction(self,plugin,action,package,bundle='',th=True):
		retval=1
		procInfo=self.plugins['rebostHelper'].rebostProcess()
		proc=None
		self._debug("Launching {} from {} (th {})".format(action,plugin,th))
		if th:
			proc=threading.Thread(target=self.plugins[plugin].execute,kwargs=({'action':action,'parms':package}))
		else:
			proc=multiprocessing.Process(target=self.plugins[plugin].execute,kwargs=({'action':action,'parms':package}))
		try:
			proc.start()
		except:
			retval=0
		return(proc)
	
	def getEpiPkgStatus(self,epifile):
		self._debug("Getting status from {}".format(epifile))
		stdout='1'
		if os.path.isfile(epifile):
			proc=subprocess.run(["{}".format(epifile),'getStatus'],stdout=subprocess.PIPE)
			stdout=proc.stdout.decode().strip()
		return (stdout)
	#def getEpiPkgStatus

	def getProgress(self):
		rs=self.plugins['rebostPrcMan'].execute(action='progress')
		return(json.dumps(rs))
	#def getProgress(self):

	def update(self):
		procInfo=self.plugins['rebostHelper'].rebostProcess()
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		self.store.clear()
		proc=multiprocessing.Process(target=self._loadAppstream,args=([procInfo['progressQ'],procInfo['resultQ']]))
		procInfo['proc']=proc
		#return(self._launchCoreProcess(procInfo,"update"))
	
	def fullUpdate(self):
		procInfo=self.plugins['rebostHelper'].rebostProcess()
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		self.store.clear()
		self.run()
		proc=multiprocessing.Process(target=self._loadAppstream,args=([procInfo['progressQ'],procInfo['resultQ']]))
		procInfo['proc']=proc
		return(self._launchCoreProcess(procInfo))

