#!/usr/bin/env python3
import sys
import importlib
import difflib
import os
import multiprocessing
import threading
import time
import json
import signal
import definitions
import logging
import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream

class Rebost():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.plugins=""
		self.gui=False
		self.propagateDbg=True
		self.cache=os.path.join("{}".format(os.environ['HOME']),".cache/rebost")
		self.cache="/tmp/.cache/rebost"
		self.cacheData=os.path.join("{}".format(self.cache),"xml")
		self.plugDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"plugins")
		self.plugins={}
		self.pluginInfo={}
		self.plugAttrMandatory=["enabled","packagekind","priority","actions","progress"]
		self.plugAttrOptional=["autostartActions","postAutostartActions"]
		self.process={}
		self.procDict={}
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
					plugInfo["%s"%item]=value
				if item in mandatory:
					mandatory.remove(item)
			if mandatory:
				#Disable plugin as not all values have been set
				if plugin!="rebostHelper":
					self._debug("Disable %s as faulting values: %s"%(plugin,mandatory))
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
				self._debug("Loading autostart actions for %s"%plugin)
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
							self._debug("Error launching %s from %s: %s"%(action,plugin,e))
		for proc in procList:
			self.process[proc]['proc'].join()
		if postactions:
			self._debug("Launching postactions")
			for plugin,actions in postactionDict.items():
				for action in actions:
					try:
						procList.append(self._execute(action,'','',plugin=plugin,th=True))
					except Exception as e:
							self._debug("Error launching %s from %s: %s"%(action,plugin,e))
	#def _autostartActions
	
	def execute(self,action,package='',extraArgs=None,extraArgs2=None):
		listProc=[]
		rebostPkgList=[]
		store=[]
		preaction=''
		selected_bundle='*'
		self._debug("Parms:\n-action: {}\n-package: {}\n-extraArgs: {}\nplugin: {}".format(action,package,extraArgs,extraArgs2))
		if extraArgs:
			for regPlugin,info in self.pluginInfo.items():
				if info.get('packagekind','package')==str(extraArgs):
					bundle=str(extraArgs)
		plugin='sqlHelper'
		if rebostPkgList==[]:
			#sqlHelper now manages all operations but load
			self._debug("Executing {} from {}".format(action,self.plugins[plugin]))
			self._debug("Parms:\n-action: {}\n-package: {}\n-extraArgs: {}\nplugin: {}".format(action,package,extraArgs,plugin))
			if extraArgs2:
				rebostPkgList.extend(self.plugins[plugin].execute(procId=0,action=action,progress='',result='',store='',args=package,extraArgs=extraArgs,extraArgs2=extraArgs))
			else:
				rebostPkgList.extend(self.plugins[plugin].execute(procId=0,action=action,progress='',result='',store='',args=package,extraArgs=extraArgs))
		#Generate the store with results and sanitize them
		if isinstance(rebostPkgList,list):
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
			(pkg,app)=rebostpkg
			store.append(app)
		return((json.dumps(store)))
	#def _sanitizeStore
	
	def _execute(self,action,package,bundle='',plugin=None,th=True):
		#action,args=action_args.split("#")
		procInfo=definitions.rebostProcess()
		plugList=[]
		procId=0
		self.procId+=1
		procIndex=self.procId
		self.process[procIndex]=procInfo.copy()
		procList=[]
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
				procId=self._executeAction(plugin,action,package,bundle,th)
				if procId:
					procList.append(procId)
		else:
			procIndex=-1
			procList=[]
		if procList:
			self.procDict[procIndex]=procList
		if procIndex in self.process.keys():
			self.process[procIndex]=self.process[self.procId].copy()
			self.process[procIndex]['plugin']=''
			self.process[procIndex]['progressQ']=''
			self.process[procIndex]['resultQ']=''
			#self.process[procIndex]['proc']=''
		else:
			print("Failed!!!")
			procIndex=-1
		return(procIndex)

	def _executeAction(self,plugin,action,package,bundle='',th=True):
		procInfo=definitions.rebostProcess()
		self.procId+=1
		self._debug("Launching {} from {} (th {})".format(action,plugin,th))
		procInfo['plugin']=plugin
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		procInfo['progress']=0
		procInfo['result']=''
		procInfo['action']=action
		procInfo['parms']=package
		if th:
			proc=threading.Thread(target=self.plugins[plugin].execute,args=(self.procId,action,procInfo['progressQ'],procInfo['resultQ'],self.store,package))
		else:
			proc=multiprocessing.Process(target=self.plugins[plugin].execute,args=(self.procId,action,procInfo['progressQ'],procInfo['resultQ'],self.store,package))
		procInfo['proc']=proc
		self.process[self.procId]=procInfo.copy()
		retval=self.procId
		try:
			proc.start()
		except:
			retval=0
		return(retval)
	
	def chkProgress(self,procId=None):
		divisor=1
		procId=int(procId)
		procIdIndex=procId
		progressDict={procIdIndex:self.process.get(procIdIndex,definitions.rebostProcess()).copy()}
		if procId<0:
			progressDict[procIdIndex]['progress']=100
			return(str(json.dumps(progressDict)))

		if procId:
			procList=self.procDict.get(procId,[])
			divisor=len(procList)
		else:
			procList=list(self.process.keys())
		for procId in procList:
			progress=self._chkProgress(procId)
			try:
				if procIdIndex==procId:
					progressDict[procIdIndex]['progress']=int(progress[procId].get('progress',0)/divisor)
					progressDict[procIdIndex]['result']=progress[procId]['result']
				else:
					progressDict[procIdIndex]['progress']+=int(progress[procId].get('progress',0)/divisor)
					progressDict[procIdIndex]['result']+=progress[procId]['result']
			except TypeError as e:
				if isinstance(progressDict[procIdIndex].get('progress',""),str):
					progressDict[procIdIndex]['progress']=0
			except org.freedesktop.DBus.Python.TypeError as e:
				if isinstance(progressDict[procIdIndex].get('progress',""),str):
					progressDict[procIdIndex]['progress']=0
			except Exception as e:
				print(e)
			self.process[procId]['progress']=progressDict[procIdIndex].get('progress',0)
			self.process[procId]['result']=progressDict[procIdIndex].get('result','')

		for clearField in ['proc','progressQ','resultQ']:
			if progressDict[procIdIndex].get(clearField):
				del (progressDict[procIdIndex][clearField])
		return(str(json.dumps(progressDict)))

	def _chkProgress(self,procId=None):
		progress={}
		if procId:
			procList=[int(procId)]
		else:
			procList=list(self.process.keys())
		for procId in procList:
			if procId in self.process.keys():
				process=self.process.get(procId,{}).copy()
				try:
					if self.process[procId].get('progress',0)<100 and self.process[procId].get('result','-1')!="-1":
						if self.process[procId]['resultQ'] and not isinstance(self.process[procId]['resultQ'],str):
							if not self.process[procId]['resultQ'].empty():
								self.process[procId]['progress']=100
								while not self.process[procId]['resultQ'].empty():
									res=self.process[procId]['resultQ'].get()
									self.process[procId]['result']=res
								self.process[procId]['proc'].terminate()
								self.process[procId]['proc'].join()
							elif not isinstance(self.process[procId]['progressQ'],str) and not self.process[procId]['progressQ'].empty():
								self.process[procId]['progress']=self.process[procId]['progressQ'].get()
						elif not self.process[procId]['progressQ'].empty():
							self.process[procId]['progress']=self.process[procId]['progressQ'].get()
				except AttributeError as e:
					print("Can't get queue msg: %s"%self.process[procId])
					self.process[procId]['progress']=100
					self.process[procId]['result']="Ended"

				except Exception as e:
					print("_chkProgress: %s"%e)
				process=self.process.get(procId,{}).copy()
#			   if process:
#				   for clearField in ['progressQ','resultQ']:
#					   del (process[clearField])
				progress[procId]=process
		return(progress)
	
	def update(self):
		procInfo=definitions.rebostProcess()
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		self.store.clear()
		proc=multiprocessing.Process(target=self._loadAppstream,args=([procInfo['progressQ'],procInfo['resultQ']]))
		procInfo['proc']=proc
		return(self._launchCoreProcess(procInfo,"update"))
	
	def fullUpdate(self):
		procInfo=definitions.rebostProcess()
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		self.store.clear()
		self.run()
		proc=multiprocessing.Process(target=self._loadAppstream,args=([procInfo['progressQ'],procInfo['resultQ']]))
		procInfo['proc']=proc
		return(self._launchCoreProcess(procInfo))

	def _launchCoreProcess(self,procInfo,action):
		procInfo['plugin']="core"
		procInfo['progress']=0
		procInfo['result']=''
		procInfo['action']=action
		procInfo['parms']=''
		procInfo['proc'].start()
		self.procId+=1
		self.procDict[self.procId]=[self.procId]
		self.process[self.procId]=procInfo.copy()
		return (self.procId)
