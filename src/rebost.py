#!/usr/bin/python3
import sys,os,time
import traceback
import json
import importlib
import dbus
import locale
import concurrent.futures as Futures
import threading
from rebostCore import _RebostCore
import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream

DBG=True

class Rebost():
	def __init__(self,*args,**kwargs):
		self.core=_RebostCore()
		self.dbg=self.core.DBG
		self.resultQueue={}
		self.thExecutor=Futures.ThreadPoolExecutor(max_workers=4)
	#def __init__(self,*args,**kwargs):

	def _debug(self,msg):
		if self.dbg==True:
			print("rebost: {}".format(msg))
	#def _debug

	def _actionCallback(self,*args,**kwargs):
		resultSet=args[0]
		self.resultQueue[resultSet.arg]=resultSet
	#def _actionCallback

	def _getSupportedFormats(self):
		formats=[]
		for bundle in self.core.supportedformats:
			if bundle==appstream.BundleKind.PACKAGE:
				formats.append("package")
			elif bundle==appstream.BundleKind.FLATPAK:
				formats.append("flatpak")
			elif bundle==appstream.BundleKind.SNAP:
				formats.append("snap")
			elif bundle==appstream.BundleKind.APPIMAGE:
				formats.append("appimage")
			elif bundle==appstream.BundleKind.UNKNOWN:
				formats.append("unknown")
		formats=list(set(formats))

		return(formats)
	#def _getSupportedFormats

	def getSupportedFormats(self):
		proc=self.thExecutor.submit(self._getSupportedFormats)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getFreedesktopCategories

	def _getFreedesktopCategories(self):
		#From freedesktop https://specifications.freedesktop.org/menu-spec/latest/category-registry.html
		result={"AudioVideo":["DiscBurning"],
			"Audio":["Midi","Mixer","Sequencer","Tuner","Recorder","Player"],
			"Video":["AudioVideoEditing","Player","Recorder","TV"],
			"Development":["Building","Debugger","IDE","GUIDesigner","Profiling","RevisionControl","Translation","Database","ProjectManagement","WebDevelopment"],
			"Education":["Art","Construction","Music","Languages","ArtificialIntelligence","Astronomy","Biology","Chemistry","ComputerScience","DataVisualization","Economy","Electricity","Geography","Geology","Geoscience","History","Humanities","ImageProcessing","Literature","Maps","Math","NumericalAnalysis","MedicalSoftware","Physics","Robotics","Spirituality","Sports","ParallelComputing"],
			"Game":["ActionGame","AdventureGame","ArcadeGame","BoardGame","BlocksGame","CardGame","Emulator","KidsGame","LogicGame","RolePlaying","Shooter","Simulation","SportsGame","StrategyGame","LauncherStore"],
			"Graphics":["2DGraphics","VectorGraphics","RasterGraphics","3DGraphics","Scanning","OCR","Photography","Publishing","Viewer"],
			"Network":["Email","Dialup","InstantMessaging","Chat","IRCCLient","Feed","FileTransfer","HamRadio","News","P2P","RemoteAcces","Telephony","TelephonyTools","VideoConference","WebBrowser","WebDevelopment"],
			"Office":["Calendar","ContactManagement","Database","Dictionary","Chart","Email","Finance","FlowChart","PDA","ProjectManagement","Presentation","Spreadsheet","WordProcessor","Photography","Publishing","Viewer"],
			"Science":["Construction","Languages","ArtificialIntelligence","Astronomy","Biology","Chemistry","ComputerScience","DataVisualization","Economy","Electricity","Geography","Geology","Geoscience","History","Humanities","Literature","Math","NumericalAnalysis","MedicalSoftware","Physics","Robotics","ParallelComputing"],
			"Settings":["Security","Accessibility"],
			"System":["Security","Emulator","FileTools","FileManager","TerminalEmulator","FileSystem","Monitor"],
			"Utility":["TextTools","TelephonyTools","Maps","Archiving","Compression","FileTools","Accessibility","Calculator","Clock","TextEditor"]
			}
		return(result)
	#def _getFreedesktopCategories

	def getFreedesktopCategories(self):
		proc=self.thExecutor.submit(self._getFreedesktopCategories)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getFreedesktopCategories

	def _searchAppByUrl(self,search,kind):
		result=[]
		initTime=int(time.time())
		searchItems=[search]
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			for app in self.core.stores["main"].get_apps():
				appUrl=app.get_url_item(kind)
				if "/es/" in search:
					searchItems.append(search.replace("/es",""))
				elif "/va/" in search:
					searchItems.append(search.replace("/va",""))
				elif "/ca/" in search:
					searchItems.append(search.replace("/ca",""))
				if appUrl in searchItems:
					result.append(app)
					break
		return(result)
	#def _searchApp

	def searchAppByUrl(self,url,kind=None):
		if kind==None:
			kind=self.core.appstream.UrlKind.HOMEPAGE
		proc=self.thExecutor.submit(self._searchAppByUrl,url,kind)
		proc.arg=len(self.resultQueue)
		self.resultQueue[proc.arg]=None
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def searchUrl(self,url):

	def _searchApp(self,search):
		result={}
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			tokens=self.core.appstream.utils_search_tokenize(search)
			if len(tokens)==0:
				tokens=search.split(" ")
			for app in self.core.stores["main"].get_apps():
				app.set_search_match(appstream.AppSearchMatch.ID|appstream.AppSearchMatch.NAME|appstream.AppSearchMatch.PKGNAME|appstream.AppSearchMatch.KEYWORD|appstream.AppSearchMatch.DESCRIPTION)
				match=app.search_matches(tokens[0])
				if len(tokens)>1:
					for s in tokens[1:len(tokens)-1]:
						match=int(app.search_matches(s)/2)
				if match>10:
					if match not in result.keys():
						result[match]=[]
					result[match].append(app)
		return(result)
	#def _searchApp

	def searchApp(self,search):
		proc=self.thExecutor.submit(self._searchApp,search)
		proc.arg=len(self.resultQueue)
		self.resultQueue[proc.arg]=None
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def searchApp

	def _showApp(self,show):
		app=[]
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			app=self.core.stores["main"].get_app_by_id_ignore_prefix(show)
			#REM this block search in all the appstream catalogues
			#for i in self.core.stores.keys():
			#	if isinstance(i,int):
			#		itapp=self.core.stores[i].get_app_by_id_ignore_prefix(show)
			#		if itapp!=None:
			#			print(itapp.get_state())
			#<---- REM
		return(app)
	#def _showApp

	def showApp(self,show):
		proc=self.thExecutor.submit(self._showApp,show)
		proc.arg=len(self.resultQueue)
		self.resultQueue[proc.arg]=None
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def showApp

	def _getApps(self):
		apps=[]
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			apps=self.core.stores["main"].get_apps()
		return(apps)
	#def _getApps
		
	def getApps(self):
		proc=self.thExecutor.submit(self._getApps)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getApps

	def _getCategories(self):
		apps=[]
		categories=[]
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			apps=self.core.stores["main"].get_apps()
		for app in apps:
			cats=app.get_categories()
			categories.extend(cats)
			categories=list(set(categories))
		return(categories)
	#def _getCategories

	def getCategories(self):
		proc=self.thExecutor.submit(self._getCategories)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getCategories

	def _getAppsPerCategory(self):
		apps=[]
		categoryapps={}
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			apps=self.core.stores["main"].get_apps()
		for app in apps:
			cats=app.get_categories()
			for cat in cats:
				if not cat in categoryapps.keys():
					categoryapps[cat]=[]
				categoryapps[cat].append(app)
		return(categoryapps)
	#def _getAppsPerCategory

	def getAppsPerCategory(self):
		proc=self.thExecutor.submit(self._getAppsPerCategory)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getAppsPerCategories

	def _getAppsInstalled(self):
		apps=[]
		installed=[]
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			apps=self.core.stores["main"].get_apps()
		for app in apps:
			if app.get_state()==appstream.AppState.INSTALLED:
				installed.append(app)
		return(installed)
	#def _getInstalledApps

	def getAppsInstalled(self):
		proc=self.thExecutor.submit(self._getAppsInstalled)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getAppsInstalled

	def _setStateForApp(self,appId,appState,bundle,temp):
		app=self.core.stores["main"].get_app_by_id_ignore_prefix(appId)
		if app!=None:
			app.set_state(appState)
			if bundle!=None:
				metadata=app.get_metadata()
				mkey="X-REBOST-{}".format(bundle)
				if appState==appstream.AppState.INSTALLED:
					state="installed"
				else:
					state="available"
				if mkey in metadata.keys():
					app.remove_metadata(mkey)
				release=metadata[mkey].split(";")[0]
				app.add_metadata(mkey,"{};{}".format(release,state))
			if temp==False:
				self.core.stores["main"].remove_app_by_id(app.get_id())
				self.core.stores["main"].add_app(app)
				self.core.export()
		return(app)
	#def _setStateForApp

	def setStateForApp(self,appId,appState,bundle=None,temp=True):
		proc=self.thExecutor.submit(self._setStateForApp,appId,appState,bundle,temp)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def setStateForApp

	def _getExternalInstaller(self):
		installer=""
		initTime=int(time.time())
		while self.core.ready==False:
			time.sleep(0.01)
			if int(time.time())-initTime>20:
				break
		if self.core.ready==True:
			installer=self.core.getExternalInstaller()
		return(installer)
	#def _getExternalInstaller

	def getExternalInstaller(self):
		proc=self.thExecutor.submit(self._getExternalInstaller)
		proc.arg=len(self.resultQueue)
		proc.add_done_callback(self._actionCallback)
		return(proc)
	#def getAppsPerCategory
