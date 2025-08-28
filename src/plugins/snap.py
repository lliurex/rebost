#!/usr/bin/env python3
import os,hashlib
import html,html2text
import gi
from gi.repository import Gio
gi.require_version ('Snapd', '2')
from gi.repository import Snapd

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.bundle=self.core.appstream.BundleKind.SNAP
		self.snap=Snapd.Client()
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("snap: {}".format(msg))
	#self _debug

	def _getCategories(self,section):
		categories=[]
		catMap={
				"artanddesign":["Graphics","Art"],
				"art-and-design":["Graphics","Art"],
				"books-and-reference":["Documentation","Education"],
				"booksandreference":["Documentation","Education"],
				"development":["Development"],
				"devicesandiot":["Development","Robotics","Electronics"],
				"devices-and-lot":["Development","Robotics","Electronics"],
				"entertainment":["Amusement"],
				"education":["Education"],
				"finance":["Office","Finance"],
				"games":["Game"],
				"healthandfitness":["Utility","Amusement"],
				"health-and-fitness":["Utility","Amusement"],
				"musicandaudio":["AudioVideo"],
				"music-and-audio":["AudioVideo"],
				"newsandweather":["Network","News"],
				"news-and-weather":["Network","News"],
				"personalisation":["Settings"],
				"photoandvideo":["AudioVideo","Graphics"],
				"photo-and-video":["AudioVideo","Graphics"],
				"productivity":["Office"],
				"security":["System","Security"],
				"serverandcloud":["Network"],
				"server-and-cloud":["Network"],
				"science":["Science"],
				"social":["Network","InstantMessaging"],
				"utilities":["Utility"]
				}
		#Snap categories aren't standard so... 
		categories=catMap.get(section.lower().replace(" ",""),["Utility"])
		return(categories)
	#def getCategories
	
	def _processSnap(self,pkg,section):
		app=self.core.appstream.App()
		name=pkg.get_name()
		ids=pkg.get_common_ids()
		if len(ids)>0:
			app.set_id(ids[0])
		else:
			app.set_id(name)
		app.add_pkgname(pkg.get_name())
		htmlparser=html2text.HTML2Text()
		htmlparser.scape_snob=True
		htmlparser.unicode_snob=True
		desc=self.core.appstream.markup_import(pkg.get_description().strip(),self.core.appstream.MarkupConvertFormat.SIMPLE)
		summary=self.core.appstream.markup_import(pkg.get_summary().strip(),self.core.appstream.MarkupConvertFormat.SIMPLE).replace("<p>","",).replace("</p>","")
		app.set_name("C",name)
		app.set_comment("C",summary)
		app.set_description("C",desc)
		icn=pkg.get_icon()
		if icn!=None:
			appicon=self.core.appstream.Icon()
			appicon.set_kind(self.core.appstream.IconKind.REMOTE)
			appicon.set_name(os.path.basename(icn))
			appicon.set_url(icn)
			app.add_icon(appicon)
		bun=self.core.appstream.Bundle()
		bun.set_kind(self.core.appstream.BundleKind.SNAP)
		bun.set_id(pkg.get_name())
		app.add_bundle(bun)
		screenshots=self.core.appstream.Screenshot()
		for scr in pkg.get_media():
			appimg=self.core.appstream.Image()
			urlimg=scr.get_url()
			if "small" in urlimg:
				appimg.set_kind(self.core.appstream.ImageKind.THUMBNAIL)
			else:
				appimg.set_kind(self.core.appstream.ImageKind.SOURCE)
			appimg.set_url(urlimg)
			screenshots.add_image(appimg)
		app.add_screenshot(screenshots)
		for cat in self._getCategories(section):
			app.add_category(cat)
		release=pkg.get_version()
		apprelease=self.core.appstream.Release()
		apprelease.set_size(self.core.appstream.SizeKind.DOWNLOAD,pkg.get_download_size())
		apprelease.set_version(release)
		if pkg.get_status==Snapd.SnapStatus.INSTALLED:
			status="installed"
			app.set_state(self.core.appstream.AppState.INSTALLED)
			apprelease.set_state(self.core.appstream.ReleaseState.INSTALLED)
		else:
			status="available"
		app.add_metadata("X-REBOST-snap","{};{}".format(release,status))
		app.add_release(apprelease)
		#URLs
		app.add_url(self.core.appstream.UrlKind.HOMEPAGE,pkg.get_store_url())
		return(app)
	#def _processSnap

	def _chkNeedUpdate(self,sectionSnaps):
		update=True
		cont=0
		for section,snaps in sectionSnaps.items():
			cont+=len(snaps)
		if cont>0:
			chash=str(cont)
			frepo=os.path.join(self.cache,"snap")
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

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		store.set_origin("snap")
		sections=[]
		try:
			sectionsSnap=self.snap.get_categories_sync()
			sections=[sc.get_name() for sc in sectionsSnap]
		except:
			print("Connection seems down")

		processed=[]
		sectionSnaps={}
		for section in sections:
			try:
				snaps,curr=self.snap.find_category_sync(Snapd.FindFlags.MATCH_NAME,section,None)
			except Exception as e:
				print(e)
				continue
			sectionSnaps.update({section:snaps})
		fxml=os.path.join(self.cache,"snap.xml")
		if self._chkNeedUpdate(sectionSnaps)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			for section,snaps in sectionSnaps.items():
				apps=[]
				for pkg in  snaps:
					if pkg.get_name() not in processed:
						processed.append(pkg.get_name())
						apps.append(self._processSnap(pkg,section))
				store.add_apps(apps)
			self.core._toFile(store,fxml)
		return(store)
	#def getAppstreamData
