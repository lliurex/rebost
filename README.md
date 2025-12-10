# README

Rebost is a software querying system for Lliurex (and probably others) distribution. 
It has a plugin mechanism for supporting almost any package manager or bundle distribution format out in the wild. Among the included plugins at least there're plugins for Slackware's slackpkg and limba bundles demonstrating the flexibility of the plugin mechanism.

# Usage

Rebost, as specified, isn't a software management per se. Its main purpose is to collect the information from the different plugins and offer it to software stores through appstream or in its own json based format. The information could be accessed through a python module or d-bus giving the stores the freedom and need to implement the management tasks (install/uninstall basically).

# Configuration

Rebost main configuration is stored at /usr/share/rebost/rebost.conf in json format.
The following keys are supported:
```
{
    "verifiedProvider": ['origins'], Array of verified origins as specified by plugins
    "onlyVerified":true/false, Load only applications included in verified providers. If an application isn't included in a verified provided is excluded from rebost. If exists then the data gets collected from all plugins
	"externalInstaller": installer's path. Path to an installer
    "release": Data release number. Release of the data format. If rebost detects a mismatch between data release and it's own data format the cache would be regenerated.
}
```

# D-Bus methods

Rebost stored data is available through d-bus interface at net.lliurex.rebost. It has the same methods and returning values as the python module.


# Python module

```
from rebost import store

client=store.client()
client.getApps()
```

As simple as import the module and use it.

## Methods
* getConfig
 ** Input: None
 * Return: { key:value } Dict of config options

* getSupportedFormats
 * Input: None
 * Return: [ str ] Array of supported formats

* getFreedesktopCategories
 * Input: None
 * Return: { category:[ subcategories ] } Dict of categories with subcategories as suggested by freedesktop

* export
 * Input: Destination file (str) Path to file
 * Return: None
 Export applications to destination file

* searchApp
 * Input: Search string (str)
 * Return: { score:application }
 Search applications by string. The search results are ordered by match score and don't search only by name, also include results by description, keywords...

* searchAppByUrl
 * Input: Searched url (str)
 * Return: application
 Search by matching url. The url is taken from the application's homepage

* showApp
 * Input: Application name (str)
 * Return: Application
 Returns the application data related to the given name

* refreshApp
 * Input: Application name (str)
 * Return: Application
 Return the application after refreshing the cache data

* getCategories
 * Input: None
 * Return: [ categories ] Array of categories
 Not used. The different package or bundle systems don't ever use standarized categories. This method returns all the categories collected

* getApps
 * Input: None
 * Return: [ applications ] Array of applications
 Returns all the applications in rebost

* getAppsPerCategory
 * Input: None
 * Return: { category: [ applications ] } A dict of applications ordered by category

* getAppsInstalled
 * Input: None
 * Return: [ applications ] Array of installed applications

* setStateForApp
 * Input: Application id, state, bundle (optional), temp (optional)
 * Output: None
 Set application's state as indicated, optionally only for a specified bundle or temporally.
 The state is one of appstreamglib.AppState. If temporally is not indicated or is true (true/false) the state is stored, otherwise only is setted after next data reload

* getExternalInstaller
 * Input: None
 * Output: Path to an application's installer
 Rebost itself doesn't do operations with applications but an external application could be configured. This method returns the path of that applications, in LliureX is the Epi Manager.

# Application data struct
Although internally rebost uses appstreamglib it outputs the information as json (or array of). The structure of an application is:
```
{
'bundle': {'kind':'id'},
'versions': {'bundleKind':'release'},
'status': {'bundleKind':'state'},
'id': 'appId',
'name': 'descriptive name',
'description': 'description of the application',
'summary': 'brief description',
'pkgname': string, default package name of the application,
'icon': string, path/url/name of the application icon,
'homepage': string, url of the applcation's homepage,
'infopage': string, url of the application's detail page,
'state': int, global status of the application matching appstreamglib.AppState.enum values
'suggests': array of related appIds,
'keywords': array of search tags,
'origin': string, 'verfied'/'unverified/other',
'categories: array of categories,
'license': string, app license,
'screenshots': array of urls pointing to screenshots,
}
```

# Plugins

A plugin in rebost is a simple python script that collects all the needed info from a package system and returns an appstreamglib store. For code examples see any of the default plugins.
They must be declared as "engine" class and include some needed methods:

* __init__
 * Input: core (optional)
This method can declare a core argument. Rebost will pass it's core to the plugin for it getting all its methods and globals available

* getAppstreamData
 * Input: None
 * Returns: Appstreamglib.store
Rebost will call this method in order of getting the applications managed by the plugin

* refresAppData (optional)
 * Input: application
 * Returns: application
If this optional method is present then rebost will call it when refresData is invoked.

# Examples

* Search of an app through d-bus using qdbus from terminal:

```
$ qdbus --system net.lliurex.rebost /net/lliurex/rebost net.lliurex.rebost.showApp antimicrox
[{"bundle": {"unknown": "accessibility.epi", "appimage": "https://files06.pling.com/api/files/download/j/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MTYxMzI5NDEyOCwibyI6IjEiLCJzIjoiOTNjOGI5NzMyMDBkMjBhNjg5ZjgzMDAyNGQxOTlmNDM4NzAwYTFhZmM4OGMzMzRiOTdmYWE4ZDlhMjRjMjNjYzhiNWVjYTkwZTc1MjFiZDBjNmZiODA0Y2ZjN2QxMjI5YTc0ZDUyNGU3M2Q0OTEzODM5NWFlOTY4ODFlMzczNzUiLCJ0IjoxNzY1Mjc1MzQ4LCJzdGZwIjpudWxsLCJzdGlwIjoiMTUxLjI0OC4yMS4yNSJ9.kGq4M8E_XnRBqmraRDJFO8QcZ0FJCLL3TZFmwbNdzHA/AntiMicroX-x86_64.AppImage", "package": "antimicro", "flatpak": "app/io.github.antimicrox.antimicrox/x86_64/stable"}, "versions": {"appimage": "", "flatpak": "3.5.1"}, "status": {"appimage": 1, "flatpak": 1}, "id": "antimicrox", "name": "antimicrox", "description": "Autoritzada - Botiga", "summary": "Autoritzada - Botiga", "pkgname": "AntiMicroX-x86_64", "icon": "https://appstream.ubuntu.com/media/noble/io/github/antimicrox.antimicrox/3153EEB4ABB12A32CBD530E95B0DB6FC/icons/128x128/antimicro_io.github.antimicrox.antimicrox.png", "homepage": "https://portal.edu.gva.es/appsedu/antimicrox/", "infopage": "https://www.appimagehub.com/p/1595189", "state": 2, "suggests": [], "keywords": ["accessibility", "accessibility.epi", "antimicrox", "antimicrox.epi", "app", "appimage", "appsedu", "controller", "game", "gamepad", "joystick", "keyboard", "lliurex", "mapping", "mouse", "release-git", "software", "x86-64", "zero", "zero-lliurex-accessibility", "zero-lliurex-antimicrox"], "origin": null, "categories": ["Education", "Qt", "Utilities", "Utility", "Various Games"], "license": "GPL-3.0+", "screenshots": ["https://appstream.ubuntu.com/media/noble/io/github/antimicrox.antimicrox/3153EEB4ABB12A32CBD530E95B0DB6FC/screenshots/image-1_1248x704.png", "https://images.pling.com/cache/770x540-4/img/00/00/50/02/87/1482076/8554c23d486386bec68418dc911d2063dceb5aa43dfa9fd95ee6b744bcdcdce1e533.png", "https://images.pling.com/cache/770x540-4/img/00/00/50/02/87/1595189/8554c23d486386bec68418dc911d2063dcebccd8d70c935f0c3b1643ceac60943a86.png", "https://appstream.ubuntu.com/media/noble/io/github/antimicrox.antimicrox/3153EEB4ABB12A32CBD530E95B0DB6FC/screenshots/image-2_1248x704.png"]}]
```

* Listing installed apps from python

```
#!/usr/bin/env python3
from rebost import store
import json

client=store.client()
installedApps=client.getAppsInstalled()
for app in json.loads(installedApps):
	print(app["id"])
```

* Plugin for Slackware's slackpkg 

```
#!/usr/bin/env python3
import os,subprocess

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
			print("slackpkg: {}".format(msg))
	#self _debug

	def _getAppsFromSlackpkg(self):
		fPackages="/var/lib/slackpkg/PACKAGES.TXT"
		apps=[]
		if os.path.exists(fPackages):
			with open(fPackages,"r",encoding="cp850") as f:
				fcontent=f.read()
			for fline in fcontent.split("\n\n"):
				fline=fline.strip()
				pkg={"description":"","name":"","summary":""}
				description=""
				name=""
				summary=""
				size=""
				app=self.core.appstream.App()
				for pkgField in fline.split("\n"):
					if pkgField.startswith("PACKAGE NAME:"):
						pkgName=":".join(pkgField.split(":")[1:])
						app.add_pkgname(pkgName)
						fieldArray=pkgName.split("-")
						fieldArray.reverse()
						release=fieldArray[2]
						arrayName=fieldArray[3:]
						arrayName.reverse()
						name="-".join(arrayName).strip()
						for l in self.core.langs:
							app.set_name(l,name)
						app.set_name("C",name)
						app.set_id(name)
						app.add_keyword("C",name)
						bun=self.core.appstream.Bundle()
						bun.set_kind(self.bundle)
						bun.set_id(pkgName)
						app.add_bundle(bun)
					elif pkgField.startswith("PACKAGE SIZE (uncompressed):"):
						size=pkgField.split(":")[1]
					elif pkgField.startswith("{}:".format(name)) and len(name)>0:
						if len(summary)==0:
							summary="{}".format(pkgField.split(":")[1])
							for l in self.core.langs:
								app.set_comment(l,summary)
							app.set_comment("C",summary)
						else:
							description+="{}".format(pkgField.split(":")[1])
							for l in self.core.langs:
								app.set_description(l,description.removesuffix("\n"))
							app.set_description("C",description.removesuffix("\n"))
				if app.get_id()!=None:
					apps.append(app)
		return(apps)
	#def _getAppsFromSlackpkg

	def _chkNeedUpdate(self,apps):
		update=True
		return(update)
	#def _chkNeedUpdate

	def getAppstreamData(self):
		#ToDo
		fxml=os.path.join(self.cache,"slackpkg.xml")
		store=self.core.appstream.Store()
		store.set_add_flags(self.core.appstream.StoreAddFlags.USE_UNIQUE_ID)
		store.set_origin("slackpkg")
		if len(store.get_apps())==0:
			apps=self._getAppsFromSlackpkg()
			store.add_apps(apps)
			self.core._toFile(store,fxml)
		self._debug("Sending {}".format(store.get_size()))
		return(store)
	#def getAppstreamData

	def refreshAppData(self,app):
		#ToDo
		return(app)
	#def refreshAppData(self,app):
#class engine

```
