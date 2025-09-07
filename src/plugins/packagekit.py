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
		apps=[]
		appsRevoked=[]
		pkgSacks=[]
		pkgIds=[]
		flags=packagekit.FilterEnum.NONE
		pkList=pk.get_packages(flags, None, self._loadCallback, None)
		pkgSacks.append(pkList.get_package_sack())
		for pkgSack in pkgSacks:
			pkgSackIds=pkgSack.get_ids()
			for ids in pkgSackIds:
				if ids.startswith("alsa"):
					continue
				if ids.startswith("auto"):
					continue
				if ids.startswith("gdc"):
					continue
				if ids.startswith("gfortran"):
					continue
				if ids.startswith("git"):
					continue
				if ids.startswith("gm2"):
					continue
				if ids.startswith("gnat"):
					continue
				if ids.startswith("gobjc"):
					continue
				if ids.startswith("golang"):
					continue
				if ids.startswith("google"):
					continue
				if ids.startswith("grub"):
					continue
				if ids.startswith("kf6"):
					continue
				if ids.startswith("lib"):
					continue
				if ids.startswith("linux"):
					continue
				if ids.startswith("ll"):
					continue
				if ids.startswith("mono"):
					continue
				if ids.startswith("node-"):
					continue
				if ids.startswith("nvidia"):
					continue
				if ids.startswith("ocam"):
					continue
				if ids.startswith("python"):
					continue
				if ids.startswith("qml-"):
					continue
				if ids.startswith("qml6"):
					continue
				if ids.startswith("qt6"):
					continue
				if ids.startswith("rust"):
					continue
				if ids.startswith("update"):
					continue
				if ids.startswith("uwsgi-"):
					continue
				if ids.startswith("vala"):
					continue
				if ids.startswith("webext-"):
					continue
				if ids.startswith("wordpress-"):
					continue
				if ids.startswith("x11"):
					continue
				if ids.startswith("xdg"):
					continue
				if ids.startswith("xorg"):
					continue
				if ids.startswith("xserver"):
					continue
				if "account" in ids:
					continue
				if "-dbg" in ids:
					continue
				if "-dev" in ids:
					continue
				if "-data" in ids:
					continue
				if "make" in ids:
					continue
				if "-tools" in ids:
					continue
				if "ubuntu" in ids.split(";")[0]:
					continue
				if "wayland" in ids:
					continue
				if ids.endswith("common"):
					continue
				pkgIds.append(ids)
	#	pkgFiles=pk.get_files(pkgIds,None,self._loadCallback,None)
	#	pkgFilesArray=pkgFiles.get_files_array()
	#	for fpkg in pkgFilesArray:
	#		fpkgList=str(fpkg.get_files())
	#		if not ".desktop" in fpkgList: #If no desktop then no app
	#			appsRevoked.append(fpkg.get_package_id())
	#			continue
	#		elif  "/autostart" in fpkgList: #If autostart then most probably isn't an end user app
	#			appsRevoked.append(fpkg.get_package_id())
		candidates=list(set(pkgIds))#-set(appsRevoked))
		candidates.sort()
		return(candidates)
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

	def _sectionMap(self,section):
		section=section.replace("desktop-","")
		sectionMap={"accessories":"Utility","admin":"", "admin-tools":"System","cli-mono":"", "comm":"", "database":"", "debug":"", "devel":"", "doc":"", "editors":"", "education":"Education",
					"electronics":"Electronics", "embedded":"", "fonts":"Office", "games":"Game", "gnome":"Office", "gnu-r":"", "gnustep":"", "graphics":"Graphics", 
					"hamradio":"", "haskell":"", "httpd":"", "interpreters":"", "introspection":"", "java":"", "javascript":"", 
					"kde":"", "kernel":"", "internet":"Network","libdevel":"", "libs":"", "lisp":"", "localization":"", "mail":"", "math":"Math", "metapackages":"", 
					"misc":"", "multimedia":"AudioVideo","net":"", "news":"", "ocaml":"", "oldlibs":"", "other":"","otherosfs":"", "perl":"", "php":"","programming": "", "python":"", 
					"ruby":"", "rust":"", "science":"Science", "shells":"TerminalEmulator", "sound":"Audio","system":"System", "tasks":"", "tex":"", "text":"","unknown":"Utility", "utils":"", 
					"vcs":"", "video":"Video", "web":"Web", "x11":"", "xfce":"", "zope":""}
		return(sectionMap.get(section,""))
	#def _sectionMap

	def _processPackages(self,pk,pkgIds):
		apps=[]
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
				app.set_trust_flags(self.core.appstream.AppTrustFlags.COMPLETE) #Needed for metadata export
				app.set_source_kind(self.core.appstream.FormatKind.UNKNOWN) #Needed for relase state
				app.set_kind(self.core.appstream.AppKind.DESKTOP)
				pkgId=detail.get_package_id()
				desc=self.core.appstream.markup_import(detail.get_description().strip(),self.core.appstream.MarkupConvertFormat.SIMPLE)
				summary=self.core.appstream.markup_import(detail.get_summary().strip(),self.core.appstream.MarkupConvertFormat.SIMPLE).replace("<p>","",).replace("</p>","")
				if "transitional" in summary.lower() or "transitional" in desc.lower():
					continue
				pkgIdArray=pkgId.split(";")
				name=pkgIdArray[0]
				release=pkgIdArray[1]
				origin=pkgIdArray[2]
				arch=pkgIdArray[3]
				app.set_id(name)
				cat=self._sectionMap(detail.get_group().to_string(detail.get_group()).lower())
				if cat=="":
					continue
				app.add_category(cat)
				app.add_pkgname(name)
				app.set_name("C",name)
				app.set_comment("C",summary)
				app.set_description("C",desc)
				app.add_keyword("C",cat)
				app.add_keyword("C",name)
				bun=self.core.appstream.Bundle()
				bun.set_kind(self.core.appstream.BundleKind.PACKAGE)
				bun.set_id(name)
				app.add_bundle(bun)
				app.set_metadata_license("CC0-1.0")
				apprelease=self.core.appstream.Release()
				apprelease.set_size(self.core.appstream.SizeKind.DOWNLOAD,detail.get_size())
				apprelease.set_version(release)
				if "auto:" in pkgId or "manual:" in pkgId or "installed" in pkgId:
					status="installed"
					app.set_state(self.core.appstream.AppState.INSTALLED)
					apprelease.set_state(self.core.appstream.ReleaseState.INSTALLED)
				else:
					status="available"
				app.add_metadata("X-REBOST-package","{};{}".format(release,status))
				app.add_release(apprelease)
				app.set_origin(origin)
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
		store.set_origin("lliurex")
		fxml=os.path.join(self.cache,"packagekit.xml")
		#if self._chkNeedUpdate(fxml)==False:
		#	store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			pk=packagekit.Client()
			pkglist=self._loadCatalogue(pk)
			apps=self._processPackages(pk,pkglist)
			store.add_apps(apps)
			self.core._toFile(store,fxml)
		self._debug("Sending {}".format(len(store.get_apps())))
		return(store)
	#def getAppstreamData

	def refreshAppData(self,app):
		oldState=app.get_state()
		#REM ToDo GET PKGID
		return(app)
		if "auto:" in pkgId or "manual:" in pkgId or "installed" in pkgId:
			status="installed"
			app.set_state(self.core.appstream.AppState.INSTALLED)
			apprelease.set_state(self.core.appstream.ReleaseState.INSTALLED)
		else:
			app.set_state(self.core.appstream.AppState.AVAILABLE)
			apprelease.set_state(self.core.appstream.ReleaseState.AVAILABLE)
			status="available"
		app.add_metadata("X-REBOST-package","{};{}".format(release,status))
		return(app)
	#def refreshAppData(self,app):
#class engine
