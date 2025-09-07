#!/usr/bin/env python3
import os,hashlib
import gi
from gi.repository import Gio
gi.require_version ('Flatpak', '1.0')
from gi.repository import Flatpak

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.bundle=self.core.appstream.BundleKind.FLATPAK
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("flatpak: {}".format(msg))
	#self _debug

	def _updateMetadata(self,flInst,flRemote):
		self._debug("Updating metadata for {}".format(flRemote.get_name()))
		flInst.update_remote_sync(flRemote.get_name(),None)
		self._debug("Updating metadata from URL {}".format(flRemote.get_url()))
		flInst.prune_local_repo()
		flRemote.set_gpg_verify(False)
		flInst.modify_remote(flRemote,None)
		flInst.update_appstream_sync(flRemote.get_name(),None,None,None)
	#def _updateMetadata

	def _initFlatpakRemotes(self):
		flInst=Flatpak.Installation.new_system(None)
		flRemote=Flatpak.Remote().new("flathub")
		flRemote.set_url('https://flathub.org/repo')#/flathub.flatpakrepo')
		flRemote.set_disabled(False)
		flInst.add_remote(flRemote,True,None)
		self._updateMetadata(flInst,flRemote)
	#def _initFlatpakRemotes

	def _getFlatpakRemotes(self,flInst):
		remotes={}
		for installer in flInst:
			self._debug("Loading {}".format(installer))
			flRemote=installer.list_remotes()
			if len(flRemote)>0:
				remotes[installer]=flRemote
		return(remotes)
	#def _getFlatpakRemotes

	def _getFlatpakMetadata(self,remotes):
		srcDir=""
		for installer,remotelist in remotes.items():
			for remote in remotelist:
				self._debug("Inspect {}".format(remote))
				srcDir=remote.get_appstream_dir().get_path()
				self._debug("flatpak srcdir: {}".format(srcDir))
				try:
					installer.update_appstream_sync(remote.get_name())
				except:
					self._debug("Error reaching remote {}".format(remote))
				self._debug("{} synced".format(srcDir))
		return(srcDir)
	#def _getFlatpakMetadata

	def _addLanguages(self,flInst):
		for installation in flInst:
			if installation.get_is_user()==True:
				installation.set_config_sync("languages","{}".format(self.core.langs[0]))
				installation.set_config_sync("extra-languages","{}".format(";".join(self.core.langs[1:])))
	#def _addLanguages

	def _chkNeedUpdate(self,fappstream):
		update=True
		chash=""
		if os.path.exists(fappstream):
			with open(fappstream,'rb') as f:
				chash=hashlib.md5(f.read()).hexdigest()
		frepo=os.path.join(self.cache,"flatpak")	
		if os.path.isfile(frepo):
			fcontent=""
			with open(frepo,'r') as f:
				fhash=f.read()
			if chash==fhash:
				update=False
			self._debug(fhash)
		self._debug(chash)
		with open(frepo,'w') as f:
			f.write(chash)
		return(update)
	#def _chkNeedUpdate

	def _setAppsState(self,flInst,store):
		installedRefs={}
		installedRefsArray=[]
		updatableRefs=[]
		for installation in flInst:
			installedRefsArray.extend(installation.list_installed_refs())
			updatableRefs.extend(installation.list_installed_refs_for_update())
		for ref in installedRefsArray:
			installedRefs[ref.get_appdata_name()]=ref.get_appdata_version()
		for app in store.get_apps():
			if app.get_name() in installedRefs:
				state="installed"
				release=installedRefs[app.get_name()]
				app.set_state(self.core.appstream.AppState.INSTALLED)
			else:
				state="available"
				release="unknown"
				releaseApp=app.get_release_default()
				if releaseApp!=None:
					release=releaseApp.get_version()
				else:
					for r in app.get_releases():
						release=r.get_version()
						break
			app.add_metadata("X-REBOST-flatpak","{};{}".format(release,state))
	#def _setAppsState

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		tmpStore=self.core.appstream.Store()
		srcDir=""
		flInst=[]
		try:
			flInst=Flatpak.get_system_installations()
		except Exception as e:
			self._debug("Error getting system installs: {}".format(e))
		remotes=[]
		if len(flInst)>0:
			remotes=self._getFlatpakRemotes(flInst)
		if len(remotes)==0:
			self._debug("Reloading repo info")
			self._initFlatpakRemotes()
			flInst=Flatpak.get_system_installations()
			remotes=self._getFlatpakRemotes(flInst)
		srcDir=self._getFlatpakMetadata(remotes)
		if srcDir=='': #When initializing for first time metada needs a reload
			srcDir=self._getFlatpakMetadata(remotes)
		self._addLanguages(flInst)
		self._debug("Loading flatpak metadata from file at {}".format(srcDir))
		fxml=os.path.join(self.cache,"flatpak.xml")
		fappstream=os.path.join(srcDir,"appstream.xml")
		if self._chkNeedUpdate(fappstream)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			store.from_file(Gio.File.parse_name(fappstream))
			self._setAppsState(flInst,store)
			self.core._toFile(store,fxml)
			self._debug("End loading flatpak metadata")
		self._debug("Sending {}".format(len(store.get_apps())))
		return(store)
	#def getAppstreamData

	def refreshAppData(self,app):
		oldState=app.get_state()
		#REM get installedRefs
		return(app)
		if app.get_name() in installedRefs:
			state="installed"
			release=installedRefs[app.get_name()]
			app.set_state(self.core.appstream.AppState.INSTALLED)
		else:
			app.set_state(self.core.appstream.AppState.AVAILABLE)
			state="available"
			release="unknown"
			releaseApp=app.get_release_default()
			if releaseApp!=None:
				release=releaseApp.get_version()
			else:
				for r in app.get_releases():
					release=r.get_version()
					break
		app.add_metadata("X-REBOST-flatpak","{};{}".format(release,state))
		return(app)
	#def refreshAppData(self,app):
#class engine
