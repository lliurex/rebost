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
		self.lastUpdate="/usr/share/rebost/tmp/as.lu"
		#self._loadStore()
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="appstream: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug(self,msg):

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
		update=self._chkNeedUpdate(store)
		if update:
			store=self._generate_store(store)
			self._debug("Get rebostPkg")
			rebostPkgList=rebostHelper.appstream_to_rebost(store)
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'appstream.db')
			self._debug("SQL loaded")
			storeMd5=str(store.get_size())
			with open(self.lastUpdate,'w') as f:
				f.write(storeMd5)
		else:
			self._debug("Skip update")
	#def _loadStore

	def _chkNeedUpdate(self,store):
		update=True
		lastUpdate=""
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
		else:
			fcontent=""
			with open(self.lastUpdate,'r') as f:
				lastUpdate=f.read()
			storeMd5=str(store.get_size())
			if storeMd5==lastUpdate:
				update=False
		return(update)
	#def _chkNeedUpdate

	def _get_appstream_catalogue(self):
		action="load"
		store=appstream.Store()
		rebostPkgList=[]
		sections=[]
		progress=0
		iconDir="/usr/share/rebost-data/icons"
		storeYml="/usr/share/rebost-data/yaml/lliurex_dists_focal_main_dep11_Components-amd64.yml"
		if os.path.isfile(storeYml):
			storeFile=Gio.File.new_for_path(storeYml)
			try:
				store.from_file(storeFile,iconDir,None)
			except Exception as e:
				print(e)
				pass
		#flags=[appstream.StoreLoadFlags.APP_INFO_SYSTEM,appstream.StoreLoadFlags.APP_INSTALL,appstream.StoreLoadFlags.APP_INFO_USER,appstream.StoreLoadFlags.DESKTOP,appstream.StoreLoadFlags.ALLOW_VETO]
		#for flag in flags:
		#	print("{}".format(flag))
		#	store.load(flag,None)
		self._debug("End loading appstream metadata")
		return(store)

	def _generate_store(self,store):
		added=[]
		rebostPkgList=[]
		iconDb=self._populate_icon_db()
		for pkg in store.get_apps():
			idx=pkg.get_id()
			#appstream has his own cache dir for icons so if present use it
			icondefault=pkg.get_icon_default()
			fname=None
			if icondefault:
				prefix=os.path.dirname(icondefault.get_prefix())
				name=icondefault.get_name()
				if not name or not prefix:
					continue
				if not name.endswith(".png"):
					name=name+".png"
				icon64=os.path.join(prefix,"64x64",name)
				icon264=os.path.join(prefix,"64x64","{}_{}".format(pkg.get_pkgname_default(),name))
				icon128=os.path.join(prefix,"128x128",name)
				icon2128=os.path.join(prefix,"128x128","{}_{}".format(pkg.get_pkgname_default(),name))
				defIcon=''
				if os.path.isfile(icon64)==True:
					defIcon=icon64
				elif os.path.isfile(icon264)==True:
					defIcon=icon264
				if os.path.isfile(icon128)==True:
					defIcon=icon128
				if os.path.isfile(icon2128)==True:
					defIcon=icon2128
				if defIcon:
					if icondefault.get_kind()==appstream.IconKind.STOCK:
						icondefault.convert_to_kind(appstream.IconKind.LOCAL)
					icondefault.set_filename(defIcon)
				fname=icondefault.get_filename()

			if fname==None:
				icon=self._get_app_icons(idx,iconDb)
				if icon:
					pkg.add_icon(icon)
			else:
				pkg.add_icon(icondefault)
			if not pkg.get_bundles():
				bundle=appstream.Bundle()
				bundle.set_id("{}".format(pkg.get_id()))
				bundle.set_kind(appstream.BundleKind.PACKAGE)
				pkg.add_bundle(bundle)
			add=False
			if add and pkg.get_id() not in added:
				try:
					if not (app.validate()):
						store.add_app(pkg)
					else:
						print(app.validate())
				except Exception as e:
					print("{0}:{1}".format(idx,e))
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

	def _populate_icon_db(self):
		appstreamIconDirs=["/var/lib/app-info/icons","/usr/share/rebost/appstream"]
		iconDb={}
		for appstreamIconDir in appstreamIconDirs:
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
		return(iconDb)

	def _get_app_icons(self,idx,iconDb):
		iconPath=''
		icon=None
		idx=os.path.basename(idx)
		idx=idx.replace(".desktop","")
		idx2=idx+"_"+idx+".png"
		idx=idx+".png"
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

def main():
	obj=appstreamHelper()
	return (obj)

