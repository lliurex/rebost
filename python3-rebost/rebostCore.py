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
		self.propagateDbg=True
		self.cache=os.path.join("{}".format(os.environ['HOME']),".cache/rebost")
		self.cache="/tmp/.cache/rebost"
		self.cacheData=os.path.join("{}".format(self.cache),"xml")
		self.plugDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"plugins")
		self.plugins={}
		self.pluginInfo={}
		self.plugAttrMandatory=["enabled","packagekind","priority","actions","progress"]
		self.plugAttrOptional=["autostartActions"]
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
		for plugin,info in self.pluginInfo.items():
			actions=info.get('autostartActions',[])
			if actions:
				self._debug("Loading autostart actions for %s"%plugin)
				priority=info.get('priority',0)
				newDict=actionDict.get(priority,{})
				newDict[plugin]=actions
				actionDict[priority]=newDict.copy()
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

	
	def execute(self,action,package='',extraArgs=None,plugin=None):
		listProc=[]
		rebostPkgList=[]
		store=[]
		preaction=''
		self._debug("Parms:\n-action: {}\n-package: {}\n-extraArgs: {}\nplugin: {}".format(action,package,extraArgs,plugin))
		if action=='install' or action=='remove':
			preaction="show"
			self._debug("Executing {} from {}".format(preaction,self.plugins['sqlHelper']))
			(pkgname,rebostPkg)=self.plugins['sqlHelper'].execute(procId=0,action=preaction,progress='',result='',store='',args=package)[0]
			bundles=json.loads(rebostPkg).get('bundle')
			if len(bundles)>1:
				store=json.dumps([{"-1":bundles}])
#			rebostPkgList.extend(self.plugins[plugin].execute(procId=0,action="show",progress='',result='',store='',args=package))
#			(bundle,package)=self._executePreInstallRemove(package,extraArgs,plugin)
		elif extraArgs:
			for regPlugin,info in self.pluginInfo.items():
				if info.get('packagekind','package')==str(extraArgs):
					bundle=str(extraArgs)
		if store==[]:
			for plugin,info in self.pluginInfo.items():
				if action in info['actions']:
					self._debug("Executing {} from {}".format(action,self.plugins[plugin]))
					self._debug("Parms:\n-action: {}\n-package: {}\n-extraArgs: {}\nplugin: {}".format(action,package,extraArgs,plugin))
					rebostPkgList.extend(self.plugins[plugin].execute(procId=0,action=action,progress='',result='',store='',args=package))

		#Generate the store with results and sanitize them
		if isinstance(rebostPkgList,list) and rebostPkgList:
				#	   xmlStore=self.plugins["rebostHelper"].rebostPkgList_to_xml(rebostPkgList)
		#   appstore=appstream.Store()
	#	   appstore.from_xml("".join(xmlStore))
			store=self._sanitizeStore(rebostPkgList,package)
		return(store)
			
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
	
	def _processBundles(self,rebostPkg):
		add=True
		#We already have flatpak icons at flatpak.wrkDir
		bundles=rebostPkg.get('bundle')
		wrkDir=""
		iconDir=""
		icon128=''
		icon64=''
		#flatpak has his own cache dir for icons so if present use it
		for plugin,info in self.pluginInfo.items():
			if info['packagekind']=="flatpak":
				icon64=os.path.join(self.plugins[plugin].wrkDir,"icons/64x64")
				icon128=os.path.join(self.plugins[plugin].wrkDir,"icons/128x128")
				break
		for bundle,idBundle in bundles.items():
			#if bundle.get_kind()==3: #flatpak
			continue
			if bundle=='flatpak': #flatpak
				if not ";" in bundle.get_id():
					add=False
					break
				icons=component.get_icons()
				for icon in icons:
					if os.path.isfile(os.path.join(icon128,icon.get_name())):
						icon.set_kind(appstream.IconKind.LOCAL)
						icon.set_filename(os.path.join(wrkDir,icon.get_name()))
						break
					elif os.path.isfile(os.path.join(icon64,icon.get_name())): 
						icon.set_kind(appstream.IconKind.LOCAL)
						icon.set_filename(os.path.join(wrkDir,icon.get_name()))
						break
		return(add)

	def _appendInfo(self,rebostPkg,oldRebostPkg):
		#if oldComponent.get_pkgname()==component.get_pkgname():
		for bundle,idBundle in rebostPkg.get('bundle',{}).items():
			if ";" in idBundle:
				oldRebostPkg['bundle'].update({bundle:idBundle})
		#Always get more complete info
		desc=oldRebostPkg.get('description','')
		newDesc=rebostPkg.get('description')
		if desc==None:
			desc=''
		if newDesc==None:
			newDesc=''
		if len(desc)<len(newDesc):
			oldRebostPkg['description']=newDesc
		cats=oldRebostPkg.get('categories')
		newCats=rebostPkg.get('categories')
		for newCat in newCats:
			if newCat not in cats:
				oldRebostPkg['categories'].append(newCat)
		for icon in rebostPkg.get('icon',[]):
				#if icon.get_kind()==appstream.IconKind.CACHED or icon.get_kind()==appstream.IconKind.LOCAL:
			oldRebostPkg['icons']=icon
#	   for release in component.get_releases():
#		   oldComponent.add_release(release)
		#if name is canonical then change to name
		oldName=oldRebostPkg.get('pkgname')
		name=rebostPkg.get('pkgname')
		if oldName and name:
			if "." in oldName and not "." in name and name:
				oldRebostPkg['pkgname']=name
		elif not oldName:
			oldRebostPkg['pkgName']=name
		return(oldRebostPkg)

	def execute2(self,action,package='',extraArgs=None,plugin=None):
		bundle=''
		self._debug("Executing %s %s"%(action,package))
		if action=='install' or action=='remove':
			(bundle,package)=self._executePreInstallRemove(package,extraArgs,plugin)
		elif extraArgs:
			for regPlugin,info in self.pluginInfo.items():
				if info.get('packagekind','package')==str(extraArgs):
						bundle=str(extraArgs)
		#Get the id
		return(self._execute(action,package,bundle,plugin))

	def _executePreInstallRemove(self,args,extraArgs='',plugin=''):
		package=definitions.rebostPkg()
		package['name']=str(args)
		result={}
		bundle=''
		showProc=self._execute("show",package['name'],plugin=plugin)
		showProcResult=json.loads(self.chkProgress(showProc))
		resultList=json.loads(self.chkProgress(showProc))
		if resultList:
#		if showProcResult:
####		while not showProcResult[str(showProc)].get('result',''):
####			showProcResult=json.loads(self.chkProgress(showProc))
####			time.sleep(0.2)
			if extraArgs:
				if extraArgs in ['package','appimage','snap','flatpak']:
					bundle=extraArgs
				else:
					bundle='package'
#			resultList=json.loads(showProcResult[str(showProc)]['result'])
			print("*****")
			self._debug(resultList)
			print("*****")
			for pkg in resultList:
				package=pkg
				if pkg['bundle']:
					if not bundle in pkg['bundle'].keys() and extraArgs:
						print("Package not supported")
						sys.exit(1)
					elif not extraArgs:
						if "package" in pkg['bundle']:
							bundle='package'
						elif "snap" in pkg['bundle']:
							bundle='snap'
						elif "appimage" in pkg['bundle']:
							bundle='appimage'
						else:
							bundle='package'
				break
			return([bundle,package])

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

	def getPlugins(self):
		pass
	
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
