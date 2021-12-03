#!/usr/bin/env python3
import os
import gi
from gi.repository import Gio
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream
import rebostHelper
import logging
import subprocess
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class appstreamHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		logging.basicConfig(format='%(message)s')
		self._debug("Loaded")
		self.enabled=True
		self.packagekind="package"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=1
		self.wrkDir='/tmp/.cache/rebost/xml/appstream'
		#self._loadStore()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("appstream: %s"%str(msg))

	def _print(self,msg):
		logging.warning("appstream: %s"%str(msg))

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			rs=self._loadStore()
		return(rs)
	#def execute

	def _loadStore(self):
		action="load"
		self._debug("Get apps")
		store=self._get_appstream_catalogue()
		self._debug("Get rebostPkg")
		rebostPkgList=rebostHelper.appstream_to_rebost(store)
		rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'appstream.db')
		self._debug("SQL loaded")

	def _get_appstream_catalogue(self):
		action="load"
		store=appstream.Store()
		rebostPkgList=[]
		sections=[]
		progress=0
		flags=[appstream.StoreLoadFlags.APP_INFO_SYSTEM,appstream.StoreLoadFlags.APP_INSTALL,appstream.StoreLoadFlags.APP_INFO_USER,appstream.StoreLoadFlags.DESKTOP,appstream.StoreLoadFlags.ALLOW_VETO]
		for flag in flags:
			store.load(flag,None)
		store=self._generate_store(store)
		self._debug("End loading appstream metadata")
		return(store)

	def _generate_store(self,store):
		added=[]
		rebostPkgList=[]
		for pkg in store.get_apps():
			idx=pkg.get_id()
			#appstream has his own cache dir for icons so if present use it
			icondefault=pkg.get_icon_default()
			if icondefault:
				prefix=icondefault.get_prefix()
				name=icondefault.get_name()
				if not name or not prefix:
					continue
				icon64=os.path.join(prefix,"64x64",name)
				icon128=os.path.join(prefix,"128x128",name)
				if os.path.isfile(icon64)==False:
					if os.path.isfile(icon128)==True:
						if icondefault.get_kind()==appstream.IconKind.STOCK:
							icondefault.convert_to_kind(appstream.IconKind.LOCAL)
						icondefault.set_filename(icon64)
				else:
					if icondefault.get_kind()==appstream.IconKind.STOCK:
						icondefault.convert_to_kind(appstream.IconKind.LOCAL)
					icondefault.set_filename(icon128)
					
				self._debug("P: {} -> {}".format(prefix,name))
			else:
				icon=self._get_app_icons(idx)
				if icon:
					pkg.add_icon(icon)
			add=False
			#if not pkg.get_bundles():
			#	bundle=appstream.Bundle()
			#	bundle.set_id("{};amd64;{}".format(pkg.get_id(),state))
			#	bundle.set_kind(appstream.BundleKind.FLATPAK)
			#	pkg.add_bundle(bundle)
			#	add=True
			#else:
			#	for bundle in pkg.get_bundles():
			#		bundle.set_id("{};amd64;{}".format(pkg.get_id(),state))
			#		bundle.set_kind(appstream.BundleKind.FLATPAK)
			#		add=True
			if add and pkg.get_id() not in added:
				try:
					if not (app.validate()):
						store.add_app(pkg)
					else:
						print(app.validate())
				except:
					pass
				added.append(pkg.get_id())
		return(store)
	#def _generate_store

	def _get_state(self,flInst,pkg):
		state="available"
		for installer in flInst:
			installed=False
			try:
				installed=installer.get_installed_ref(0,pkg.get_name())
			except:
				try:
					installed=installer.get_installed_ref(1,pkg.get_name())
				except:
					pass
			if installed:
				state="installed"
				break
		return(state)
	#def _get_state

	def _get_app_icons(self,idx):
		appstreamIconDir="/var/lib/app-info/icons"
		iconPath=''
		icon=None
		idx=os.path.basename(idx)
		idx=idx.replace(".desktop","")
		idx2=idx+"_"+idx+".png"
		idx=idx+".png"
		iconDb={}
		if os.path.isdir(appstreamIconDir)==True:
			for iconDir in os.listdir(appstreamIconDir):
				pathDir=os.path.join(appstreamIconDir,iconDir)
				if os.path.isdir(pathDir)==True:
					icon64=os.path.join(pathDir,"64x64")
					icon128=os.path.join(pathDir,"128x128")
					iconFiles=os.listdir(icon64)
					iconDb[icon64]=iconFiles
					iconFiles=os.listdir(icon128)
					iconDb[icon128]=iconFiles
		for path,iconFiles in iconDb.items():
			if idx in iconFiles: 
				iconPath=os.path.join(path,"{}".format(idx))
				break
			elif idx2 in iconFiles: 
				iconPath=os.path.join(path,"{}".format(idx2))
				break
		if iconPath!='':
			icon=appstream.Icon()
			icon.set_kind(appstream.IconKind.LOCAL)
			icon.set_filename(iconPath)
		return(icon)
	#def _get_app_icons

	def _init_flatpak_repo(self):
		cmd=['/usr/bin/flatpak','remote-add','--if-not-exists','flathub','https://flathub.org/repo/flathub.flatpakrepo']
		subprocess.run(cmd)
	#def _init_flatpak_repo

def main():
	obj=appstreamHelper()
	return (obj)

