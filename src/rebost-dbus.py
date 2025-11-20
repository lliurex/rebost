#!/usr/bin/env python3
import sys
import zlib
import json
import signal
import dbus,dbus.service,dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import rebost
import rebostHelper
import logging

class rebostDbusMethods(dbus.service.Object):
	def __init__(self,bus_name,*args,**kwargs):
		super().__init__(bus_name,"/net/lliurex/rebost")
		logging.basicConfig(format='%(message)s')
		self.dbg=kwargs["dbg"]
		signal.signal(signal.SIGUSR2, self._reloadSignal)
		signal.signal(signal.SIGUSR1, self._updatedSignal)
		signal.signal(signal.SIGALRM, self._beginUpdateSignal)
		self.rebost=rebost.Rebost()
	#def __init__

	def _debug(self,msg):
		if self.dbg:
			logging.debug("rebost-dbus: %s"%str(msg))
			print("rebost-dbus: %s"%str(msg))
	#def _debug

	def _beginUpdateSignal(self,*args,**kwargs):
		self.beginUpdateSignal()
	#def _beginUpdateSignal

	def _reloadSignal(self,*args,**kwargs):
		self.reloadSignal()
	#def _reloadSignal

	def _updatedSignal(self,*args,**kwargs):
		self.updatedSignal()
	#def _updatedSignal

	def _print(self,msg):
		logging.info("rebost-dbus: %s"%str(msg))
	#def _print

	@dbus.service.signal("net.lliurex.rebost")
	def beginUpdateSignal(self):
		pass
	#def storeLoaded

	@dbus.service.signal("net.lliurex.rebost")
	def reloadSignal(self):
		pass
	#def storeLoaded

	@dbus.service.signal("net.lliurex.rebost")
	def updatedSignal(self):
		pass
	#def storeUpdated

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='a{sv}')
	def toggleLock(self):
		ret=self.rebost.toggleLock()
		resultList=ret.result()
		return (resultList)
	#def toggleLock
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='as')
	def getSupportedFormats(self):
		ret=self.rebost.getSupportedFormats()
		resultList=ret.result()
		return (resultList)
	#def getFreedesktopCategories

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='a{sv}')
	def getConfig(self):
		ret=self.rebost.getConfig()
		resultList=ret.result()
		return (resultList)
	#def getConfig

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='a{sas}')
	def getFreedesktopCategories(self):
		ret=self.rebost.getFreedesktopCategories()
		resultList=ret.result()
		return (resultList)
	#def getFreedesktopCategories

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='as')
	def getCategories(self):
		ret=self.rebost.getCategories()
		resultList=ret.result()
		return (resultList)
	#def getCategories

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getApps(self):
		ret=self.rebost.getApps()
		resultList=ret.result()
		getResult=rebostHelper.appstreamToRebost(resultList)
		return(json.dumps(getResult))
	#def getApps

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getAppsPerCategory(self):
		ret=self.rebost.getAppsPerCategory()
		resultDict=ret.result()
		getResult={}
		for cat,apps in resultDict.items():
			getRebostApps=rebostHelper.appstreamToRebost(apps)
			getResult[cat]=getRebostApps
		return(json.dumps(getResult))
	#def search

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def getAppsInCategory(self,category):
		ret=self.rebost.getAppsPerCategory()
		resultDict=ret.result()
		getResult={}
		getRebostApps=rebostHelper.appstreamToRebost(resultDict.get(category,[]))
		getResult[category]=getRebostApps
		return(json.dumps(getResult))
	#def getAppsPerCategory

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getAppsInstalled(self):
		ret=self.rebost.getAppsInstalled()
		resultList=ret.result()
		getResult=rebostHelper.appstreamToRebost(resultList)
		return(json.dumps(getResult))
	#def getAppsInstalled

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getAppsInstalledPerCategory(self):
		ret=self.rebost.getAppsInstalledPerCategory()
		resultList=ret.result()
		getResult=rebostHelper.appstreamToRebost(resultList)
		return(json.dumps(getResult))
	#def getAppsInstalled

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getPendingApps(self):
		ret=self.rebost.getApps()
		resultList=ret.result()
		getResult=[]
		for app in rebostHelper.appstreamToRebost(resultList):
			if app.get("unavailable",False)==True and app.get("unauthorized",False)==False:
				getResult.append({"name":app.get("name"),"alias":app.get("aliases"),"summary":app.get("summary"),"url":app.get("homepage"),"bundles":app.get("bundle")})
		return(json.dumps(getResult))
	#def getAppsInstalled


	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def search(self,pkgname):
		pkgname=pkgname.lower()
		ret=self.rebost.searchApp(pkgname)
		resultDict=ret.result()
		priority=list(resultDict.keys())
		priority.sort()
		priority.reverse()
		searchResult=[]
		for p in priority:
			searchResult.extend(resultDict[p])
		searchResult=rebostHelper.appstreamToRebost(searchResult)
		return(json.dumps(searchResult))
	#def search

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def searchAppByUrl(self,url):
		kind=self.rebost.core.appstream.UrlKind.HOMEPAGE
		ret=self.rebost.searchAppByUrl(url,kind)
		resultList=ret.result()
		searchResult=rebostHelper.appstreamToRebost(resultList)
		return(json.dumps(searchResult))
	#def search

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def showApp(self,pkgname):
		ret=self.rebost.showApp(pkgname)
		resultList=ret.result()
		getResult=rebostHelper.appstreamToRebost(resultList)
		return(json.dumps(getResult))
	#def showApp

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def refreshApp(self,pkgname):
		ret=self.rebost.refreshApp(pkgname)
		resultList=ret.result()
		getResult=rebostHelper.appstreamToRebost(resultList)
		return(json.dumps(getResult))
	#def refreshApp

	def _getStateFromValue(self,value):
		if value==1:
			appState=self.rebost.core.appstream.AppState.INSTALLED
		elif value==2:
			appState=self.rebost.core.appstream.AppState.AVAILABLE
		elif value==4:
			appState=self.rebost.core.appstream.AppState.UPDATABLE
		elif value==7:
			appState=self.rebost.core.appstream.AppState.INSTALLING
		elif value==8:
			appState=self.rebost.core.appstream.AppState.REMOVING
		else:
			appState=self.rebost.core.appstream.AppState.UNKNOWN
		return appState
	#def _getStateFromValue

	def _setAppState(self,appId,state,bundle=None,temp=True):
		appState=self._getStateFromValue(state)
		ret=self.rebost.setStateForApp(appId,appState,bundle,temp)
		app=ret.result()
		return(app)
	#def _setAppState

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssi', out_signature='s')
	def setAppState(self,appId,bundle,state):
		app=self._setAppState(appId,state,bundle,False)
		getResult=rebostHelper.appstreamToRebost(app)
		return(json.dumps(getResult))
	#def setAppState

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='si', out_signature='s')
	def setAppStateTmp(self,appId,state):
		app=self._setAppState(appId,state)
		getResult=rebostHelper.appstreamToRebost(app)
		return(json.dumps(getResult))
	#def setAppStateTmp

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getExternalInstaller(self):
		ret=""
		try:
			result=self.rebost.getExternalInstaller()
			ret=result.result()
		except Exception as e:
			print("D-BUS Exception: {}".format(e))
			ret=""
		return ret
	#def getExternalInstaller
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def export(self,fxml=''):
		ret=self.rebost.export(fxml)
		print("Exported to {}".format(ret))
		return (ret)
	#def export
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def getUpgradableApps(self,user=""):
		ret="Not implemented yet"
		return (ret)
	#def getUpgradableApps(self):
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='b', out_signature='b')
	def update(self,force=False):
		ret=True
		#self.beginUpdateSignal()
		try:
			self.rebost.forceUpdate(force)
		except:
			ret=False
#		ret = zlib.compress(ret.encode(),level=1)
		return ret
	#def update

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def restart(self):
		ret=True
		try:
			self.rebost.restart()
		except Exception as e:
			print("Critical error relaunching")
			print(str(e))
			ret=False
		return (ret)
	#def restart(self):

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def getLockStatus(self):
		return(self.getConfig().get("onlyVerified",False))
	#def getLockStatus
#class rebostDbusMethods
	
class rebostDBus():
	def __init__(self): 
		self.dbg=False
		if len(sys.argv)>1:
			if sys.argv[0]=="-d":
				self.dbg=True
		self._setDbus()
	#def __init__

	def _setDbus(self):
		DBusGMainLoop(set_as_default=True)
		loop = GLib.MainLoop()
		# Declare a name where our service can be reached
		try:
			bus_name = dbus.service.BusName("net.lliurex.rebost",
											bus=dbus.Bus(),
											do_not_queue=True)
		except dbus.exceptions.NameExistsException:
			print("service is already running")
			sys.exit(1)

		rebostDbusMethods(bus_name,dbg=self.dbg)
		# Run the loop
		try:
			loop.run()
		except KeyboardInterrupt:
			print("keyboard interrupt received")
		except Exception as e:
			print("Unexpected exception occurred: '{}'".format(str(e)))
		finally:
			loop.quit()
	#def _setDbus
#class rebostDBus

rebostDBus()
