#!/usr/bin/env python3
import os,json,subprocess
from urllib import request
import gi
from gi.repository import Gio

mapFileDir="/usr/share/rebost-data/lists.d/"
release=subprocess.check_output(["/usr/bin/lliurex-version","-n"],universal_newlines=True,encoding="utf8")
release="llx{}".format(release.split(".")[0])
EDUAPPS_MAP=os.path.join(mapFileDir,release,"eduapps.map")
if not os.path.exists(EDUAPPS_MAP):
	for d in os.scandir(mapFileDir):
		if d.name.startswith("llx"):
			release=d.name
			EDUAPPS_MAP=os.path.join(mapFileDir,release,"eduapps.map")
			break
EDUAPPS_MAP_URL="https://github.com/lliurex/rebost-data/raw/refs/heads/master/lists.d/{}/eduapps.map".format(release)

YAML_DIR="/usr/share/rebost-data/yaml/{}".format(release)
if not os.path.exists(YAML_DIR):
	YAML_DIR=os.dirname(YAML_DIR)
	for d in os.scandir(YAML_DIR):
		if d.name.startswith("llx"):
			release=d.name
			YAML_DIR=os.path.join(YAML_DIR,release)
			break


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
			print("lliurex: {}".format(msg))
	#self _debug

	def _chkNeedUpdate(self,fappstream):
		return(True)
	#def _chkNeedUpdate

	def _fetchCatalogue(self,url=""):
		if len(url)==0:
			url=EDUAPPS_URL
		content=''
		req=request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with request.urlopen(req,timeout=2) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			self._debug("Couldn't fetch {}".format(url))
			self._debug(e)
		return(content)
	#def _fetchCatalogue

	def _getAppseduMapFixes(self):
		mapFixes={"nodisplay":[],"aliases":{}}
		jcontent={}
		if os.path.exists(EDUAPPS_MAP):
			with open(EDUAPPS_MAP,"r") as f:
				mapFixes=json.loads(f.read())
		mapFixesUrlContent=self._fetchCatalogue(EDUAPPS_MAP_URL)
		if len(mapFixesUrlContent)>0:
			try:
				jcontent=json.loads(mapFixesUrlContent)
			except Exception as e:
				print(e)
				jcontent={}
		if len(jcontent)>0:
			if jcontent!=mapFixes:
				jcontentNodisplay=jcontent.get("nodisplay",[])
				nodisplay=list(set(mapFixes["nodisplay"]+jcontentNodisplay))
				mapFixes["nodisplay"]=nodisplay
				jcontentAliases=jcontent.get("aliases",{})
				mapFixes["aliases"].update(jcontentAliases)
		return(mapFixes)
	#def _getAppseduMapFixes

	def getAppstreamData(self):
		self._debug("Loading from specified locations")
		store=self.core.appstream.Store()
		if os.path.exists(YAML_DIR):
			for f in os.scandir(YAML_DIR):
				if f.name.endswith(".yml"):
					store.from_file(Gio.File.parse_name(f.path),"/usr/share/rebost-data/icons/cache")
		else:
			self._debug("Can't find {}".format(fdir))
		mapFixes=self._getAppseduMapFixes()
		for app in store.get_apps(): #Add bundle for pkgs
			if app.get_id().endswith("_zmd"):
				app.set_id(app.get_id().removesuffix("_zmd"))
			if app.get_id().endswith(".desktop"):
				app.set_id(app.get_id().removesuffix(".desktop"))
			if app.get_id() in mapFixes["nodisplay"] or app.get_name() in mapFixes["nodisplay"]:
				self._debug("Discard {}".format(app.get_id()))
				continue
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
		return(None)
	#def refreshAppData
#class engine
