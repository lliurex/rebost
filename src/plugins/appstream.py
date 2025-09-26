#!/usr/bin/env python3
import os

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.bundle=self.core.appstream.BundleKind.PACKAGE
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("appstream: {}".format(msg))
	#self _debug

	def _chkNeedUpdate(self,fappstream):
		return(True)
	#def _chkNeedUpdate

	def getAppstreamData(self):
		self._debug("Loading from default locations")
		store=self.core.appstream.Store()
		store.load(self.core.appstream.StoreLoadFlags.APP_INFO_SYSTEM,None)
		for app in store.get_apps(): #Add bundle for pkgs
			pkgnames=app.get_pkgnames()
			if len(pkgnames)>0:
				bun=self.core.appstream.Bundle()
				bun.set_kind(self.bundle)
				bun.set_id(pkgnames[0])
				app.add_bundle(bun)
		self._debug("Sending {}".format(store.get_size()))
		return(store)
	#def getAppstreamData

	def refreshAppData(self,app):
		return(app)
	#def refreshAppData
#class engine
