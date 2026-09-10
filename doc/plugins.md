# Plugins

A plugin in rebost is a simple python script that collects all the needed info from a package system and returns an appstreamglib store. For code examples see any of the default plugins.
They must be declared as "engine" class and include some needed methods and attributes:

* __init__
	* Input: core (optional)
	  - core: rebost Core (if any)
	  - bundle: Bundle Kind, from [appstream bundleKind enum](https://lazka.github.io/pgi-docs/AppStreamGlib-1.0/enums.html#AppStreamGlib.BundleKind)
   
This method can declare a core argument. Rebost will pass it's core to the plugin for exposing its plubic methods and globals

* getAppstreamData
	* Input: None
	* Returns: [Appstreamglib.store](https://lazka.github.io/pgi-docs/#AppStreamGlib-1.0/classes/Store.html)
   
Rebost will call this method in order of getting the addon catalogue

* refreshAppData (optional)
	* Input: application
	* Returns: application
   
If this optional method is present then rebost will call it when refreshApp is invoked.


# Examples

* plugin implementation for Slackware's slackpkg 

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
		#ToDo
		update=True
		return(update)
	#def _chkNeedUpdate

	def getAppstreamData(self):
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

