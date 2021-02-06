#!/usr/bin/env python3
import sys
import importlib
import os
import multiprocessing
import time
import json
import signal
import definitions
import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStream as appstream

class Rebost():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		self.plugins=""
		self.propagateDbg=True
		self.cache="%s/.cache/rebost"%os.environ['HOME']
		self.cacheData="%s/xml"%self.cache
		self.plugDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"plugins")
		self.plugins={}
		self.pluginInfo={}
		self.plugAttrMandatory=["enabled","packagekind","priority","actions","progress"]
		self.plugAttrOptional=["autostartActions"]
		self.process={}
		self.procDict={}
		self.store=appstream.Pool()
		self._loadPlugins()
		self._loadPluginInfo()
		if self.propagateDbg:
			self._setPluginDbg()
		self._loadAppstream()
		self.procId=1

	def run(self):
		self._autostartActions()
	#def run

	def _debug(self,msg):
		if self.dbg:
			print("rebost: %s"%str(msg))
	#def _debug
	
	def _setPluginDbg(self):
		for plugin,pluginObject in self.plugins.items():
			try:
				pluginObject.setDebugEnabled()
			except Exception as e:
				print(e)
	#def _setPluginDbg

	def _loadAppstream(self,progressQ=None,resultQ=None):
		self.store.clear_metadata_locations()
		cont=len(os.listdir(self.cacheData))
		inc=50/cont
		progress=0
		for folder in os.listdir(self.cacheData):
			self.store.add_metadata_location(self.cacheData)
			if os.path.isdir(os.path.join(self.cacheData,folder)):
				self._debug("Loading apps from %s"%os.path.join(self.cacheData,folder))
				self.store.add_metadata_location(os.path.join(self.cacheData,folder))
				if progressQ:
					progress+=inc
					progressQ.put(progress)
		try:
			self.store.load()
		except Exception as e:
			self._debug("Invalid files: %s"%(e))
		self._sanitizeStore(progressQ)
		if progressQ:
			progressQ.put(100)
			resultQ.put(str(json.dumps([{'name':'update','description':'Ready'}])))
	#def _loadAppstream
	

	def _sanitizeStore(self,progressQ=None):
		pkgDict={}
		components=self.store.get_components()
		progress=50
		inc=50/len(components)
		for component in components:
			name=''
			name=component.get_id().split(".")[-1].lower()
			name=name.replace("_","-")
			if name in pkgDict.keys():
				component=self._appendInfo(component,pkgDict[name])
			if not component.get_bundles():
				if not component.get_pkgname():
					continue
			add=self._processBundles(component)
			if progressQ:
				progress+=inc
				progressQ.put(int(progress))

			if add:
				pkgDict[name]=component
		self.store.clear()
		for name,component in pkgDict.items():
			self.store.add_component(component)
	#def _sanitizeStore
	
	def _processBundles(self,component):
		add=True
		#We already have flatpak icons at flatpak.wrkDir
		bundles=component.get_bundles()
		for bundle in bundles:
			if bundle.get_kind()==3: #flatpak
				if not ";" in bundle.get_id():
					add=False
					break
				wrkDir=""
				iconDir=""
				for plugin,info in self.pluginInfo.items():
					if info['packagekind']=="flatpak":
						iconDir=os.path.join(self.plugins[plugin].wrkDir,"icons/64x64")
						wrkDir=os.path.join(self.plugins[plugin].wrkDir,"icons/128x128")
						break
				icons=component.get_icons()
				for icon in icons:
					if os.path.isfile(os.path.join(wrkDir,icon.get_name())):
						icon.set_kind(appstream.IconKind.LOCAL)
						icon.set_filename(os.path.join(wrkDir,icon.get_name()))
						break
					elif os.path.isfile(os.path.join(wrkDir.replace("128x128","64x64"),icon.get_name())): 
						icon.set_kind(appstream.IconKind.LOCAL)
						icon.set_filename(os.path.join(wrkDir,icon.get_name()))
		return(add)

	def _appendInfo(self,component,oldComponent):
			#if oldComponent.get_pkgname()==component.get_pkgname():
		for bundle in component.get_bundles():
			if ";" in bundle.get_id():
				oldComponent.add_bundle(bundle)
		#Always get more complete info
		desc=oldComponent.get_description()
		newDesc=component.get_description()
		if desc==None:
			desc=''
		if newDesc==None:
			newDesc=''
		if len(desc)<len(newDesc):
			oldComponent.set_description(newDesc)
		cats=oldComponent.get_categories()
		newCats=component.get_categories()
		for newCat in newCats:
			if newCat not in cats:
				oldComponent.add_category(newCat)
		for icon in component.get_icons():
				#if icon.get_kind()==appstream.IconKind.CACHED or icon.get_kind()==appstream.IconKind.LOCAL:
			oldComponent.add_icon(icon)
		for release in component.get_releases():
			oldComponent.add_release(release)
		#if name is canonical then change to name
		if oldComponent.get_pkgname() and component.get_pkgname():
			if "." in oldComponent.get_pkgname() and not "." in component.get_pkgname():
				oldComponent.set_pkgnames([component.get_pkgname()])
		elif not oldComponent.get_pkgname() :
			oldComponent.set_pkgnames([component.get_pkgname()])
		return(oldComponent)

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
						pluginObject=imp.main()
					except Exception as e:
						self._debug("Failed importing %s: %s"%(plugin,e))
						continue
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
		actionList.sort(reverse=True)
		for priority in actionList:
			for plugin,actions in actionDict[priority].items():
					for action in actions:
							#try:
							self._execute(action,'','',plugin=plugin)
						#except Exception as e:
						#	self._debug("Error launching %s from %s: %s"%(action,plugin,e))
	
	def execute(self,action,package='',extraArgs=None,plugin=None):
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
		time.sleep(0.5)
		showProcResult=json.loads(self.chkProgress(showProc))
		if showProcResult:
			while not showProcResult[str(showProc)].get('result',''):
				showProcResult=json.loads(self.chkProgress(showProc))
				time.sleep(0.2)
			if extraArgs:
				if extraArgs in ['package','appimage','snap','flatpak']:
					bundle=extraArgs
				else:
					bundle='package'
			resultList=json.loads(showProcResult[str(showProc)]['result'])
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

	def _execute(self,action,package,bundle='',plugin=None):
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
				procId=self._executeAction(plugin,action,package,bundle)
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
			self.process[procIndex]['proc']=''
		else:
			print("Failed!!!")
			procIndex=-1
		return(procIndex)

	def _executeAction(self,plugin,action,package,bundle=''):
		procInfo=definitions.rebostProcess()
		self.procId+=1
		self._debug("Launching %s from %s"%(action,plugin))
		procInfo['plugin']=plugin
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		procInfo['progress']=0
		procInfo['result']=''
		procInfo['action']=action
		procInfo['parms']=package
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
#				if process:
#					for clearField in ['progressQ','resultQ']:
#						del (process[clearField])
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
		return(self._launchCoreProcess(procInfo))
	
	def fullUpdate(self):
		procInfo=definitions.rebostProcess()
		procInfo['progressQ']=multiprocessing.Queue()
		procInfo['resultQ']=multiprocessing.Queue()
		self.store.clear()
		self.run()
		proc=multiprocessing.Process(target=self._loadAppstream,args=([procInfo['progressQ'],procInfo['resultQ']]))
		procInfo['proc']=proc
		return(self._launchCoreProcess(procInfo))

	def _launchCoreProcess(self,procInfo):
		procInfo['plugin']="core"
		procInfo['progress']=0
		procInfo['result']=''
		procInfo['action']='update'
		procInfo['parms']=''
		procInfo['proc'].start()
		self.procId+=1
		self.procDict[self.procId]=[self.procId]
		self.process[self.procId]=procInfo.copy()
		return (self.procId)
