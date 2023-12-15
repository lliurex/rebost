#!/usr/bin/env python3
import os,sys
import gi
from gi.repository import Gio
gi.require_version ('Flatpak', '1.0')
from gi.repository import Flatpak
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream
import rebostHelper
import logging
import subprocess
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class flatpakHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		logging.basicConfig(format='%(message)s')
		self._debug("Loaded")
		self.enabled=True
		self.packagekind="flatpak"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=1
		self.wrkDir='/tmp/.cache/rebost/xml/flatpak'
		self.lastUpdate="/usr/share/rebost/tmp/fp.lu"
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="flatpak: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug

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
		store=self._get_flatpak_catalogue()
		update=self._chkNeedUpdate(store)
		if update:
			self._debug("Get rebostPkg")
			rebostPkgList=rebostHelper.appstream_to_rebost(store)
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'flatpak.db')
			self._debug("SQL loaded")
			storeMd5=str(store.get_size())
			with open(self.lastUpdate,'w') as f:
				f.write(storeMd5)
		else:
			self._debug("Skip update")

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

	def _get_flatpak_catalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		progress=0
		flInst=''
		store=appstream.Store()
		#metadata=appstream.Metadata()
		(srcDir,flInst)=self._get_flatpak_metadata()
		if srcDir=='':
		#When initializing for first time metada needs a reload
			(srcDir,flInst)=self._get_flatpak_metadata()
		try:
			self._debug("Loading flatpak metadata from file at {}".format(srcDir))
			#with open(os.path.join(srcDir,"appstream.xml"),'r') as f:
			#	fcontent=f.read()
			#store.from_xml(fcontent)
			store.from_file(Gio.File.parse_name(os.path.join(srcDir,"appstream.xml")))
		except Exception as e:
			print(e)
		#self._debug("Formatting flatpak metadata")
		for app in store.get_apps():
			idx=app.get_id()
			icon=self._get_app_icons(srcDir,idx)
			if icon:
				app.add_icon(icon)
		self._debug("End loading flatpak metadata")
		return(store)

	def _get_flatpak_metadata(self):
		#Get all the remotes, copy appstream to wrkdir
		flInst=[]
		srcDir=''
		try:
			flInst=Flatpak.get_system_installations()
		except Exception as e:
			print("Error getting flatpak remote: {}".format(e))
		for installer in flInst:
			self._debug("Loading {}".format(installer))
			flRemote=installer.list_remotes()
			if not flRemote:
				self._init_flatpak_repo()
				self._debug("Reloading {}".format(installer))
				break
			for remote in flRemote:
				srcDir=remote.get_appstream_dir().get_path()
				self._debug("flatpak srcdir: {}".format(srcDir))
				try:
					installer.update_appstream_sync(remote.get_name())
				except:
					self._debug("Error reaching remote {}".format(remote))
				self._debug("{} synced".format(srcDir))
		return(srcDir,flInst)
	#def _get_flatpak_metadata

	def _generate_store(self,store,flInst,srcDir):
		added=[]
		rebostPkgList=[]
		for pkg in store.get_apps():
			idx=pkg.get_id()
			state=self._get_state(flInst,pkg)
			#flatpak has his own cache dir for icons so if present use it
			icon=self._get_app_icons(srcDir,idx)
			if icon:
				pkg.add_icon(icon)
			add=False
			if not pkg.get_categories():
				pkg.add_category("Utility")
			if not pkg.get_bundles():
				bundle=appstream.Bundle()
				bundle.set_id("{};amd64;{}".format(pkg.get_id(),state))
				bundle.set_kind(appstream.BundleKind.FLATPAK)
				pkg.add_bundle(bundle)
				add=True
			else:
				for bundle in pkg.get_bundles():
					bundle.set_id("{};amd64;{}".format(pkg.get_id(),state))
					bundle.set_kind(appstream.BundleKind.FLATPAK)
					add=True
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
			fname=pkg.get_id_filename()
			flistName=fname.split("/")
			if len(flistName)>1:
				fname=fname.split("/")[1]
			try:
				#installed=installer.get_installed_ref(0,pkg.get_name())
				installed=installer.get_installed_ref(0,fname)
			except Exception as e:
				try:
					#installed=installer.get_installed_ref(1,pkg.get_name())
					installed=installer.get_installed_ref(1,fname)
				except Exception as e:
					pass
			if installed:
				state="installed"
				break
		return(state)
	#def _get_state

	def _get_app_icons(self,srcDir,idx):
		iconPath=''
		icon=None
		idx=idx.replace(".desktop","")
		iconDirs=[]
		baseDir=os.path.dirname(srcDir)
		for d in os.listdir(baseDir):
			f=os.path.join(baseDir,d,"icons")
			if os.path.isdir(f):
				iconDirs.append(f)
		for iconDir in iconDirs:

			icon64=os.path.join(iconDir,"64x64")
			icon128=os.path.join(iconDir,"128x128")
			if os.path.isfile(os.path.join(icon128,"{}.png".format(idx))):
				iconPath=os.path.join(icon128,"{}.png".format(idx))
				break
			elif os.path.isfile(os.path.join(icon64,"{}.png".format(idx))):
				iconPath=os.path.join(icon64,"{}.png".format(idx))
				break
		if iconPath!='':
			icon=appstream.Icon()
			icon.set_kind(appstream.IconKind.LOCAL)
			icon.set_filename(iconPath)
		return(icon)
	#def _get_app_icons

	def _init_flatpak_repo(self):
		cmd=['/usr/bin/flatpak','remote-add','--if-not-exists','flathub','https://flathub.org/repo/flathub.flatpakrepo']
		try:
			subprocess.run(cmd)
		except Exception as e:
			print(e)
			print("Flatpak source disabled")
	#def _init_flatpak_repo

def main():
	obj=flatpakHelper()
	return (obj)

