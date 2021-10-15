#!/usr/bin/env python3
import os
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
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self._debug("Loaded")
		self.enabled=True
		self.packagekind="flatpak"
		self.actions=["load","install","remove"]
		self.autostartActions=["load"]
		self.priority=1
		self.wrkDir='/tmp/.cache/rebost/xml/flatpak'
		#self._loadStore()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("flatpak: %s"%str(msg))

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
		self._debug("Get rebostPkg")
		rebostPkgList=rebostHelper.appstream_to_rebost(store)
		rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'flatpak.db')
		self._debug("SQL loaded")

	def _get_flatpak_catalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		progress=0
		flInst=''
		store=appstream.Store()
		#metadata=appstream.Metadata()
		try:
			#Get all the remotes, copy appstream to wrkdir
			flInst=Flatpak.get_system_installations()
			for installer in flInst:
				self._debug("Loading {}".format(installer))
				flRemote=installer.list_remotes()
				if not flRemote:
					self._init_flatpak_repo()
					self._debug("Reloading {}".format(installer))
					flRemote=installer.list_remotes()
				for remote in flRemote:
					srcDir=remote.get_appstream_dir().get_path()
					self._debug(srcDir)
					installer.update_appstream_sync(remote.get_name())
					self._debug("{} synced".format(srcDir))
		except Exception as e:
			print("Error getting flatpak remote: {}".format(e))

		try:
			self._debug("Loading flatpak metadata from file at {}".format(srcDir))
			#with open(os.path.join(srcDir,"appstream.xml"),'r') as f:
			#	fcontent=f.read()
			#store.from_xml(fcontent)
			store.from_file(Gio.File.parse_name(os.path.join(srcDir,"appstream.xml")))
		except Exception as e:
			print(e)
		added=[]
		rebostPkgList=[]
		self._debug("Formatting flatpak metadata")
		for pkg in store.get_apps():
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
			add=False
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
		self._debug("End loading flatpak metadata")
		return(store)

	def _init_flatpak_repo(self):
		cmd=['/usr/bin/flatpak','remote-add','--if-not-exists','flathub','https://flathub.org/repo/flathub,flatpakrepo']
		subprocess.run(cmd)

def main():
	obj=flatpakHelper()
	return (obj)

