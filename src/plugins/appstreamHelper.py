#!/usr/bin/env python3
import os,stat,distro
import json
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
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self._debug("Loaded")
		self.enabled=True
		self.packagekind="package"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=0
		dbCache="/tmp/.cache/rebost"
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER"))
		if os.path.exists(self.rebostCache)==False:
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.wrkDir=os.path.join(self.rebostCache,"xml","appstream")
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","as.lu")
		self.pkgfile="/usr/share/rebost/lists.d/eduapps.map"
		self.ignored=["rebost","rebost-gui"]
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
		self._debug("Get apps")
		restrictedYml="/usr/share/rebost-data/yaml/eduapps.yml"
		store=self._loadCatalogueFromFiles([restrictedYml])
		(release,codename)=self._getReleaseCodename()
		storeYml=["/usr/share/rebost-data/yaml/{0}/lliurex_dists_{1}_main_dep11_Components-amd64.yml".format(release,codename),
			"/usr/share/rebost-data/yaml/{0}/lliurex_dists_{1}_universe_dep11_Components-amd64.yml".format(release,codename)]
		fullstore=self._loadCatalogueFromFiles(storeYml)
		update=self._chkNeedUpdate(store)
		if update:
			if len(store.get_apps())<=0:
				store=fullstore
			store=self._generateStore(store,fullstore)
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

	def _getReleaseCodename(self):
		release="llx23"
		cmd=["/usr/bin/lliurex-version","-n"]
		try:
			out=subprocess.check_output(cmd,encoding="utf8",universal_newlines=True)
		except Exception as e:
			print(e)
			#out=distro.codename()
		if isinstance(out,str):
			release=out.strip()[0:out.rindex(".")]
			if release.isdigit():
				release="llx{}".format(release)
			else:
				release="llx23"
		codename=distro.codename()
		return(release,codename)
	#def _getReleaseCodename

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

	def _loadCatalogueFromFiles(self, storeYmlFiles=[]):
		store=appstream.Store()
		sections=[]
		progress=0
		iconDir="/usr/share/rebost-data/icons"
		for storeYml in storeYmlFiles:
			if storeYml=="":
				continue
				#storeYml="/usr/share/rebost-data/yaml/lliurex_restricted.yml"
			if os.path.isfile(storeYml):
				self._debug("Loading data from {}".format(storeYml))
				storeFile=Gio.File.new_for_path(storeYml)
				try:
					store.from_file(storeFile,iconDir,None)
				except Exception as e:
					print(e)
					pass
		self._debug("End loading appstream metadata")
		return(store)
	#def _loadCatalogueFromFiles

	def _loadAppstreamCatalogue(self):
		store=appstream.Store()
		flags=[appstream.StoreLoadFlags.APP_INFO_SYSTEM,appstream.StoreLoadFlags.APP_INSTALL,appstream.StoreLoadFlags.APP_INFO_USER,appstream.StoreLoadFlags.DESKTOP,appstream.StoreLoadFlags.ALLOW_VETO]
		for flag in flags:
			store.load(flag,None)
		self._debug("End loading full appstream metadata")
		return(store)
	#def _loadAppstreamCatalogue

	def _generateStore(self,restrictedstore,fullstore=None):
		added=[]
		store=appstream.Store()
		rebostPkgList=[]
		iconDb=self._populateIconDb()
		#Load ignored apps from map file if present
		self._loadIgnoredApps()

		for pkg in restrictedstore.get_apps():
			pkgname=pkg.get_pkgname_default()
			if pkgname in self.ignored:
				continue
			if fullstore:
				fullPkg=fullstore.get_app_by_pkgname(pkgname)
				if fullPkg:
					pkg=fullPkg
			idx=pkg.get_id()
			#appstream has his own cache dir for icons so if present use it
			icondefault=pkg.get_icon_default()
			#state is not working
			#Do a best effort, get launchable and check if exists
			pkg.set_state(2)
			for i in pkg.get_launchables():
				if os.path.exists("/usr/share/applications/{}".format(i.get_value())):
					pkg.set_state(1)
			fname=None
			if icondefault:
				icondefault=self._setIconFname(pkg,icondefault)
			if fname==None:
				icon=self._getAppIcons(idx,iconDb)
				if icon:
					pkg.add_icon(icon)
			else:
				pkg.add_icon(icondefault)
			if not pkg.get_bundles():
				bundle=appstream.Bundle()
				#bundle.set_id("{}".format(pkg.get_id()))
				bundle.set_id("{}".format(pkgname))
				bundle.set_kind(appstream.BundleKind.LIMBA)
				pkg.add_bundle(bundle)
			if pkg.get_id() not in added:
				#Validate is time-consuming so disable...
#				try:
#					if not (pkg.validate(appstream.AppValidateFlags.NONE)):
#						store.add_app(pkg)
#					else:
#						print(pkg.validate(appstream.AppValidateFlags.NONE))
#				except Exception as e:
#					print("{0}:{1}".format(idx,e))
				store.add_app(pkg)
				added.append(pkg.get_id())
		return(store)
	#def _generateStore

	def _loadIgnoredApps(self):
		if os.path.exists(self.pkgfile):
			apps=[]
			with open(self.pkgfile,"r") as f:
				apps=json.loads(f.read())
			for app in apps.keys():
				if apps[app]=="" and app not in self.ignored:
					self.ignored.append(app)
	#def _loadIgnoredApps

	def _setIconFname(self,pkg,icondefault):
		prefix=icondefault.get_prefix()
		if prefix:
			prefix=os.path.dirname(icondefault.get_prefix())
		name=icondefault.get_name()
		if not name or not prefix:
			return
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
		return(icondefault)
	#def _setIconFname

	def _populateIconDb(self):
		appstreamIconDirs=["/var/lib/app-info/icons","/usr/share/rebost-data/icons"]
		iconDb={}
		for appstreamIconDir in appstreamIconDirs:
			if os.path.isdir(appstreamIconDir)==True:
				for iconDir in os.listdir(appstreamIconDir):
					pathDir=os.path.join(appstreamIconDir,iconDir)
					if os.path.isdir(pathDir)==True:
						icon64=os.path.join(pathDir,"64x64")
						icon128=os.path.join(pathDir,"128x128")
						if os.path.isdir(icon64):
							iconFiles=os.listdir(icon64)
							iconDb[icon64]=iconFiles
						if os.path.isdir(icon128):
							iconFiles=os.listdir(icon128)
							iconDb[icon128]=iconFiles
						for i in os.scandir(pathDir):
							if i.name.endswith(".png"):
								if pathDir not in iconDb:
									iconDb[pathDir]=[]
								iconDb[pathDir].append(i.path)
		return(iconDb)

	def _getAppIcons(self,idx,iconDb):
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
	#def _getAppIcons

def main():
	obj=appstreamHelper()
	return (obj)

