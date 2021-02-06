#!/usr/bin/env python3
import os
import gi
from gi.repository import Gio
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstreamglib
import json
import re
import urllib
import random
import time
import datetime
import gettext
from bs4 import BeautifulSoup
import tempfile
import definitions
import html2text

class appstreamHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.enabled=True
		self.packagekind=""
		self.actions=["load","search","show","list"]
		self.autostartActions=["load"]
		self.priority=1
		self.store=None
		self.progressQ={}
		self.progress={}
		self.resultQ={}
		self.result={}
		self.wrkDir='/home/lliurex/.cache/rebost/xml/appstream'
		self.metadataLoc=['/usr/share/metainfo',self.wrkDir]
		self.idPrefixes=['org.packagekit','io.snapcraft','io.appimage','org.flathub']
		#self.store=appstream.Pool()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			print("appstream: %s"%str(msg))

	def execute(self,procId,action,progress,result,store,args=''):
		if action in self.actions:
			self.progressQ[action]=progress
			self.resultQ[action]=result
			self.progress[action]=0
			if action=='load':
				self._loadStore(action)
			if action=='search':
				self.store=store
				self._searchStore(args.lower())
			if action=='show':
				self.store=store
				self._showPkg(args.lower())
			if action=='list':
				self.store=store
				self._listPkgs(args.lower())

	def _callback(self,action,progress):
			self.progress[action]=self.progress[action]+progress
			self.progressQ[action].put(self.progress[action])

	def _loadStore(self,action):
		store=appstreamglib.Store()
		icon_dir='/usr/share/icons/hicolor/128x128'
		flags=[appstreamglib.StoreLoadFlags.APP_INFO_SYSTEM,appstreamglib.StoreLoadFlags.APP_INSTALL,appstreamglib.StoreLoadFlags.APP_INFO_USER,appstreamglib.StoreLoadFlags.DESKTOP,appstreamglib.StoreLoadFlags.ALLOW_VETO]
		total=len(flags)
		iteration=int(100/total)
		for flag in flags:
			try:
				self._debug("Loading "+str(flag))
				store.load(flag)
			except:
				print ("Failed to load"+str(flag))
			self._callback(action,iteration)
		if not os.path.exists(self.wrkDir):
			os.makedirs(wrkDir)
		storeFile=Gio.File.new_for_path(self.wrkDir+"/appstream.xml")
		store.to_file(storeFile,appstreamglib.NodeToXmlFlags.NONE)
		self.resultQ[action].put(str(json.dumps([{'name':'load','description':'Ready'}])))
	#def load_store

	def _searchStore(self,tokens):
		action='search'
		self._debug("Searching app %s"%tokens)
		applist=[]
		resultList=[]
		app=None
		if tokens:
			appList=self.store.search(tokens)
			for app in appList:
				resultList.append(self._set_pkg_info(app))
		self.progress[action]=100
		self.resultQ[action].put(str(json.dumps(resultList)))
		self.progressQ[action].put(self.progress[action])

	def _showPkg(self,package):
		action="show"
		self._debug("Showing app %s"%package)
		app=None
		for prefix in self.idPrefixes: 
			app=self.store.get_components_by_id("{}.{}".format(prefix,package))
			if app:
				break
		resultList=[]
		if app:
			resultList.append(self._set_pkg_info(app))
		self.progress[action]=100
		self.resultQ[action].put(str(json.dumps(resultList)))
		self.progressQ[action].put(self.progress[action])

	def _listPkgs(self,*args):
		action="list"
		categories=[]
		resultList=[]
		if args:
			categories=args
		self._debug("Listing cat: {}".format(categories))
		#Segfaults!!!!
		#categoryAppps=self.store.get_components_by_categories(categories)
		#Workaround
		categoryApps=self.store.get_components()
		total=len(categoryApps)
		inc=100/total
		for app in categoryApps:
			for cat in categories:
				if cat.capitalize() in app.get_categories():
					resultList.append(self._set_pkg_info(app))
					break
			self.progress[action]+=inc
			self.progressQ[action].put(int(self.progress[action]))

		self.progress[action]=100
		self.resultQ[action].put(str(json.dumps(resultList)))
		self.progressQ[action].put(self.progress[action])
	
	def _set_pkg_info(self,app):
		pkg=definitions.rebostPkg()
		if isinstance(app,list):
			app=app[0]
		pkg['id']=app.get_id()
		pkg['kind']=app.get_kind()
		if app.get_pkgname():
			pkg['pkgname']=app.get_pkgname()
		else:
			pkg['pkgname']=app.get_id()
		pkg['name']=app.get_name()

		pkg['icon']=''
		icons=app.get_icons()
		if icons:
			for icon in icons:
				if icon.get_filename(): #appstreamglib.IconKind.LOCAL:
					pkg['icon']=icon.get_filename()
				elif icon.get_url(): #appstreamglib.IconKind.REMOTE:
					pkg['icon']=icon.get_url()
				else:
					pkg['icon']=icon.get_name()
		if not pkg['icon']:
			pkg['icon']=''
		bl={}
		bundleDef={1:'package',2:'package',3:'flatpak',4:'appimage',5:'snap',6:'tarball'}
		for bundle in app.get_bundles():
			bundleStr=''
			bundleStr=bundleDef.get(bundle.get_kind(),'package')
			bid=bundle.get_id()
			if bid:
				bl.update({bundleStr:bid})
				#Get state
				if 'installed' in bid:
					pkg['state'].update({bundleStr:1})
				else:
					pkg['state'].update({bundleStr:0})
		pkg['bundle']=bl
		if app.get_description():
			pkg['description']=html2text.html2text(app.get_description(),"lxml")
		else:
			pkg['description']=html2text.html2text(app.get_summary(),"lxml")
		pkg['summary']=html2text.html2text(app.get_summary(),"lxml")
		pkg['installerUrl']=app.get_url(appstreamglib.UrlKind.BUGTRACKER)
		pkg['categories']=app.get_categories()
		if len(pkg['categories'])>1 and "Utility" in pkg['categories']:
			pkg['categories'].remove('Utility')

		for releaseObj in app.get_releases():
			release=releaseObj.get_version()
			if release.startswith("snap-"):
				pkg['versions'].update({'snap':release.replace("snap-","")})
			elif release.startswith("appimage-"):
				pkg['versions'].update({'appimage':release.replace("appimage-","")})
			elif release.startswith("package-"):
				pkg['versions'].update({'package':release.replace("package-","")})
			else:
				pkg['versions'].update({'flatpak':release})
		return(pkg)

def main():
	obj=appstreamHelper()
	return (obj)
