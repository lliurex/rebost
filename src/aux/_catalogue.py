#!/usr/bin/python3
from gi.repository import Gio
gi.require_version('AppStream', '1.0')
from gi.repository import AppStream as appstream

class _rebostApps:
	def __init__(self,*args):
		self.core=args[0]
		self.config=self.core.config
		self.aux=self.core.aux
		self.DBG=self.core.DBG
	#def __init__

	def _getOldData(self,app,donor):
		appDesc={}
		appSumm={}
		donorDesc={}
		donorSumm={}
		icon=None
		if app.get_icon_path()!=None:
			icon=app.get_icon_default()
		for l in self.langs:
			desc=app.get_description(l)
			if desc==None:
				desc=""
			summ=app.get_comment(l)
			if summ==None:
				summ=""
			appDesc.update({l:{"desc":desc,"summ":summ}})
			desc=donor.get_description(l)
			if desc==None:
				desc=""
			summ=donor.get_comment(l)
			if summ==None:
				summ=""
			donorDesc.update({l:{"desc":desc,"summ":summ}})
		return(appDesc,appSumm,donorDesc,donorSumm,icon)
	#def _getOldData

	def _doSubsumeApps(self,app,donor):
		#It seems strange but both subsumes are needed
		#add all info, honouring previous subsume
		#subsume_full will need lot of flags to load all the info, only put empty fields (including installed status aka metadata)
		appDesc,appSumm,donorDesc,donorSumm,icon=self._getOldData(app,donor)
		app.subsume(donor)
		extendFlags=appstream.AppSubsumeFlags.BUNDLES|\
			appstream.AppSubsumeFlags.METADATA|\
			appstream.AppSubsumeFlags.KEYWORDS|\
			appstream.AppSubsumeFlags.ICONS|\
			appstream.AppSubsumeFlags.URL|\
			appstream.AppSubsumeFlags.SCREENSHOTS
		app.subsume_full(donor,appstream.AppSubsumeFlags.BOTH_WAYS|extendFlags)
		replaceFlags=appstream.AppSubsumeFlags.STATE|\
				appstream.AppSubsumeFlags.NAME
		app.subsume_full(donor,appstream.AppSubsumeFlags.REPLACE|replaceFlags)
		for l,desc in donorDesc.items():
			if len(appDesc[l]["desc"])<len(desc["desc"]):
				app.set_description(l,desc["desc"])
			if len(appDesc[l]["summ"])<len(desc["summ"]):
				app.set_comment(l,desc["summ"])
		if icon!=None:
			app.add_icon(icon)
		app.subsume(donor)
		return(app)
	#def _doSubsumeApps

	def _preLoadVerified(self,verifiedOrigins):
		store=appstream.Store()
		for idx in verifiedOrigins:
			for app in self.stores[idx].get_apps():
				mergeApp=self._preMergeApp(app)
				oldApp=store.get_app_by_id(mergeApp.get_id())
				if oldApp!=None:
					store.remove_app(oldApp)
					try:
						mergeApp=self._doSubsumeApps(mergeApp,oldApp)
					except Exception as e:
						self._error(e,msg="_preLoadVerified")
				mergeApp.set_origin("verified")
				noDsp=self.mapFixes.get("nodisplay",[])
				appKnownAs=[mergeApp.get_id(),mergeApp.get_name()]
				appKnownAs.extend(mergeApp.get_pkgnames())
				allApps=list(set(noDsp))
				allApps.extend(list(set(appKnownAs)))
				if len(allApps) != len(set(allApps)):
					self._debug("Hidden -> {}".format(mergeApp.get_name()))
					mergeApp.add_metadata("X-REBOST-hidden","{}".format(mergeApp.get_id()))
				store.add_app(mergeApp)
		self._debug("Verified table count: {}".format(store.get_size()))
		return(store)
	#def _preLoadVerified

	def _preMergeApp(self,app):
		newId=app.get_id()
		aliases=self.mapFixes.get("aliases",{})
		if len(app.get_bundles())>0:
			if app.get_bundles()[0].get_kind()==appstream.BundleKind.FLATPAK:
				fixes=["gdevelop"]
				splitId=app.get_id().replace(".desktop","").split(".")
				newId=splitId[-1]
				if len(splitId)>2:
					if splitId[1].lower() in fixes:
						newId=splitId[1]
			elif app.get_bundles()[0].get_kind()==appstream.BundleKind.APPIMAGE:
				newId=app.get_id().strip()
				#Canonical name
				if newId.count("-")==2:
					newId=newId.split("-")[0]
				#Kdenlive (perhaps others)
				elif newId.count("_")==3:
					newId=newId.split("_")[0]
				else:
					tmpId=""
					while tmpId=="":
						arrayId=newId.strip().split(".")
						for item in arrayId:
							for i in item.split("-"):
								if i.isdigit():
									if tmpId!="":
										continue
								tmpId="{}.{}".format(tmpId,i)
					newId=tmpId.strip().rstrip(".").lstrip(".")
				newId=newId.lower().removesuffix(".appimage").split(".")[-1]
		#	elif app.get_bundles()[0].get_kind()==appstream.BundleKind.SNAP:
			else:
				newId=app.get_id().removesuffix(".desktop")
				if newId.count(".")>1: #It seems canonical
					tags=newId.split(".")
					tags.reverse()
					fallback=""
					for tag in tags:
						if tag.isnumeric():
							fallback=tag
							continue
						newId=tag
						break
		else:
			newId=app.get_id().removesuffix(".desktop")
			if newId.count(".")>1: #It seems canonical
				newId=newId.split(".")[-1]
		newId=newId.lower().removeprefix(".").removesuffix(".")
		if newId in aliases.keys():
			newId=aliases[newId]
		if newId!=app.get_id():
			app.set_id(newId)
		return (app)
	#def _preMergeApp

	def _generateCatalogue(self):
		self._debug("Filling catalogue")
		self.stores["mainB"]=appstream.Pool() #Include all apps
		verifiedOrigins=self.config._getVerifiedOrigins()
		self.mapFixes=self.map.getMapFixes()
		if len(verifiedOrigins)>0:
			self.stores["mainB"]=self._preLoadVerified(verifiedOrigins)

	def _mergeApps2(self):
		self._debug("Filling work table")
		self.stores["mainB"]=appstream.Store() #Include all apps
		self.stores["mainB"].set_add_flags(appstream.StoreAddFlags.USE_MERGE_HEURISTIC) #Include verified apps
		verifiedOrigins=self._getVerifiedOrigins()
		self.mapFixes=self.getMapFixes()
		if len(verifiedOrigins)>0:
			self.stores["mainB"]=self._preLoadVerified(verifiedOrigins)
		self.ready=False
		self.stores["main"].remove_all()
		self.stores["main"].set_add_flags(appstream.StoreAddFlags.USE_MERGE_HEURISTIC)
		self.stores["main"].add_apps(self.stores["mainB"].dup_apps())
		aliases=self.mapFixes.get("aliases",{})
		for storeId in self.stores.keys():
			if storeId in verifiedOrigins:
				self._debug("Verified {}".format(storeId))
				continue
			if isinstance(storeId,int):
				self._debug("Process {} ({})".format(storeId,self.stores[storeId].get_size()))
				for app in self.stores[storeId].get_apps():
					appId=app.get_id()
					if appId in aliases.keys():
						self._debug("Change ID from {0} to {1}".format(appId,aliases[appId]))
						app.set_id(aliases[appId])
					originId=app.get_id()
					mergeApp=self._preMergeApp(app)
					tmpid=mergeApp.get_id()
					oldApp=self.stores["main"].get_app_by_id(tmpid)
					if oldApp==None:
						oldApp=self.stores["main"].get_app_by_id(originId.lower())
						if oldApp!=None:
							oldApp.set_id(tmpid)
					if oldApp!=None:
						try:
							self.stores["main"].remove_app(oldApp)
							mergeApp=self._doSubsumeApps(mergeApp,oldApp)
						except Exception as e:
							self._error(e,msg="_mergeApps")
					oldApp=self.stores["mainB"].get_app_by_id(tmpid)
					noDsp=self.mapFixes.get("nodisplay",[])
					appKnownAs=[mergeApp.get_id(),mergeApp.get_name()]
					appKnownAs.extend(mergeApp.get_pkgnames())
					allApps=list(set(noDsp))
					allApps.extend(list(set(appKnownAs)))
					if len(allApps) != len(set(allApps)):
						self._debug("Hidden -> {}".format(mergeApp.get_name()))
						mergeApp.add_metadata("X-REBOST-hidden","{}".format(mergeApp.get_id()))
					mergeApp.set_origin("unverified")
					if oldApp!=None:
						self.stores["mainB"].remove_app(oldApp)
						mergeApp.set_origin("verified")
						self.stores["mainB"].add_app(mergeApp)
					self.stores["main"].add_app(mergeApp)
		config=self.readConfig()
		if config.get("onlyVerified",False)==True:
			self.loadToggle()
	#def _mergeApps

