#!/usr/bin/python3
import os,time
import gi
from gi.repository import Gio
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit
import json
import hashlib
import html

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
			print("packagekit: {}".format(msg))
	#self _debug

	def _loadCallback(self,*args):
		return
	#def _loadCallback

	def _loadCatalogue(self,pk):
		self._debug("Getting pkg list")
		flags=packagekit.FilterEnum.GUI
		pkList=pk.get_packages(flags, None, self._loadCallback, None)
		pkgSack=pkList.get_package_sack()
		return (pkgSack)
	#def _loadCatalogue

	def _chkNeedUpdate(self,pklist):
		update=True
		chash=str(pklist.get_size())
		frepo=os.path.join(self.cache,"packagekit")	
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

	def _processPackages(self,pk,pklist):
		apps=[]
		pkgIds=pklist.get_ids()
		pkgDetails=[]
		pkgCount=0
		inc=5200
		total=inc
		processed=0
		pkgCount=len(pkgIds)
		self._debug("Total packages {}".format(pkgCount))
		while processed<pkgCount:
			self._debug("Processing pkg list {}".format(processed))
			####  REM WIP ON OPTIMIZATION
			# Calls to packagekit are too expensive so it's needed to replace them
			# Apparently we need a get_details call for retrieving categories
			# Perhaps it's possible to use pkg.group property but isn't working
			pkDetails=pk.get_details(pkgIds[processed:total], None, self._loadCallback, None)
			details=pkDetails.get_details_array()
			for detail in details:
				app=self.core.appstream.App()
				desc=html.escape(detail.get_description().strip())
				summary=detail.get_description().split("\n")[0]
				pkgId=detail.get_package_id().split(";")
				name=pkgId[0]
				release=pkgId[1]
				origin=pkgId[2]
				arch=pkgId[3]
				cat=detail.get_group().to_string(detail.get_group()).lower()
				if len(pkgId)>4:
					installed=True
				app.set_id(name)
				app.add_pkgname(name)
				for l in self.core.langs:
					app.set_name(l,name)
					app.set_comment(l,summary)
					app.set_description(l,desc)
					app.add_keyword(l,cat)
					app.add_keyword(l,name)
				bun=self.core.appstream.Bundle()
				bun.set_kind(self.core.appstream.BundleKind.PACKAGE)
				bun.set_id(name)
				app.add_bundle(bun)
				apprelease=self.core.appstream.Release()
				apprelease.set_size(self.core.appstream.SizeKind.DOWNLOAD,detail.get_size())
				apprelease.set_version(release)
				app.add_release(apprelease)
				apps.append(app)
			self._debug("End processing pkg list")
			processed=total
			total+=inc
			if total>pkgCount:
				total=pkgCount
			time.sleep(0.001)
		return(apps)
	#def _processPackages

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		fxml=os.path.join(self.cache,"packagekit.xml")
		pk=packagekit.Client()
		pkglist=self._loadCatalogue(pk)
		if self._chkNeedUpdate(pkglist)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			apps=self._processPackages(pk,pkglist)
			store.add_apps(apps)
			self.core._toFile(store,fxml)
		return(store)
	#def getAppstreamData
