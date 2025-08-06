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
		print(resultSet)
		self.resultQueue[resultSet.arg]=resultSet
	#def _actionCallback

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
				if match>50:
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
			app=self.core.stores["main"].get_apps_by_id(show)
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
		self.core.ready=False
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
