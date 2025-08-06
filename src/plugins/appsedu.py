#!/usr/bin/env python3
import os,shutil,stat
import json
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
import hashlib
from bs4 import BeautifulSoup as bs

EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"
EDUAPPS_MAP="/usr/share/rebost-data/lists.d/llx25/eduapps.map"
EDUAPPS_MAP_URL="https://github.com/lliurex/rebost-data/raw/refs/heads/master/lists.d/llx25/eduapps.map"
i18n={'CAD':"Engineering",
	'Música':"Music",
	'Gràfics':"Graphics",
	'Vídeo':"Video",
	'Ingenieria':"Engineering",
	'Àudio':"Audio",
	'Tecnologia':"Robotics", 
	'Tecnología':"Robotics", 
	'Multimèdia':"AudioVideo", 
	'Matemàtiques':"Math", 
	'Video':"Video", 
	'Electrònica':"Electronics", 
	'Utilitats':"Utility", 
	'Gamificació':"Education",
	'Robótica':"Robotics", 
	'Ciències':"Science",
	'Geografia':"Geography",
	'Ofimàtica':"Office",
	'Informàtica':"ComputerScience",
	'Musica':"Music",
	'Intel·ligència Artificial':"ArtificialIntelligence", 
	'Programació':"Development", 
	'Fotografia':"Photography", 
	'Disseny':"Engineering",
	'Física':"Physics",
	'Enginyeria':"Engineering",
	'Química':"Chemistry",
	'Presentacions':"Presentation"}

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.bundle=self.core.appstream.BundleKind.UNKNOWN
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("eduapps: {}".format(msg))
	#self _debug

	def _fetchCatalogue(self,url=""):
		if len(url)==0:
			url=EDUAPPS_URL
		content=''
		req=Request(url, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urllib.request.urlopen(req,timeout=2) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			print("Couldn't fetch {}".format(url))
			print("{}".format(e))
		return(content)
	#def _fetchCatalogue

	def _getAppseduMapFixes(self):
		mapFixes={"nodisplay":[],"alias":{}}
		if os.path.exists(EDUAPPS_MAP):
			with open(EDUAPPS_MAP,"r") as f:
				mapFixes=json.loads(f.read())
		mapFixesUrlContent=self._fetchCatalogue(EDUAPPS_MAP_URL)
		if len(mapFixesUrlContent)>0:
			try:
				jcontent=json.loads(mapFixesUrlContent)
			except:
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

	def _getRealCategory(self,cat):
		cat=i18n.get(cat,cat)
		return(cat)
	#def _getRealCategory

	def _getAppsEduCatalogue(self):
		self._debug("Fetching {}".format(EDUAPPS_URL))
		rawcontent=self._fetchCatalogue()
		fraw=os.path.join(self.cache,"appsedu.raw")
		with open(fraw,"w") as f:
			f.write(rawcontent)
		bscontent=bs(rawcontent,"html.parser")
		appInfo=bscontent.find_all("td",["column-1","column-2","column-5","column-7","column-8"])
		eduApps=[]
		candidate=None
		columnAuth=None
		columnName=None
		columnCats=None
		columnIcon=None
		columnPkgName=None
		categories=[]
		mapFixes=self._getAppseduMapFixes()
		for column in appInfo:
			full=False
			if (column.attrs["class"][0]=="column-1"):
				columnIcon=column.img
			if (column.attrs["class"][0]=="column-2"):
				columnName=column.find_all("a",href=True)
			if (column.attrs["class"][0]=="column-5"):
				columnCats=column.text
			if (column.attrs["class"][0]=="column-7"):
				columnAuth=column.text
			if (column.attrs["class"][0]=="column-8"):
				columnPkgName=column.text
				#Some apps should be hidden as are pure system apps (drkonqui...)
				#or apps included within another (kde-connect related stuff...)
				#or for some other reason (xterm..)
				#The 1st approach is based on category and authorizaton status
				#but there're many apps misscatalogued so is disabled ATM
				#if columnAuth.lower().endswith("sistema"):
				#	if "utili" in columnCats.lower():
				#		columnAuth=None
				#		columnName=None
				#		columnIcon=None
				#		continue
				#if len(columnPkgname.strip())>0:
				if len(columnCats.strip())>0:
					full=True
			if full==True:
				for data in columnName:
					infopage=data["href"]
					candidate=os.path.basename(infopage.strip("/"))
				if candidate:
					if columnIcon==None:
						self._debug("NO ICON FOR {}".format(candidate))
						continue
					pkgIcon=columnIcon["src"]
					if candidate:
						if candidate in mapFixes["nodisplay"]:
							continue
						if candidate in mapFixes["aliases"]:
							print("Was {} -> {}".format(columnPkgName,mapFixes["aliases"].get(candidate,"")))
							columnPkgName=mapFixes["aliases"].get(candidate,"")
						cats=[]
						#Categories must be mapped 'cause are translated
						for cat in columnCats.split(","):
							realCat=self._getRealCategory(cat.strip())
							if len(realCat)>0 and realCat not in cats:
								cats.append(realCat)
						if len(columnPkgName.strip())==0:
							columnPkgName=candidate
						eduApps.append({"app":candidate,"icon":pkgIcon,"auth":columnAuth,"categories":cats,"alias":columnPkgName,"infopage":infopage})
						candidate=None
						categories.extend(cats)
				columnAuth=None
				columnName=None
				columnIcon=None
				columnPkgname=None
		return(eduApps)
	#def _getAppsEduCatalogue

	def _getRawContent(self):
		rawcontent=""
		fraw=os.path.join(self.cache,"appsedu.raw")
		if os.path.exists(fraw):
			with open(fraw,"r") as f:
				rawcontent=f.read()
		return(rawcontent)
	#def _getRawContent
	
	def _chkNeedUpdate(self,rawcontent):
		update=True
		chash=hashlib.md5(rawcontent.encode("utf-8")).hexdigest()
		frepo=os.path.join(self.cache,"appsedu")	
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

	def _processApp(self,eduapp):
		app=self.core.appstream.App()
		pkgname=eduapp.get("app","").strip()
		if len(pkgname)==0:
			pkgname=eduapp["app"]
		app.set_id("gva.appsedu.{}".format(pkgname))
		app.add_pkgname(pkgname)
		for l in self.core.langs:
			app.set_name(l,pkgname)
			app.set_comment(l,eduapp["auth"])
			app.set_description(l,eduapp["auth"])
		app.add_url(self.core.appstream.UrlKind.HOMEPAGE,eduapp["infopage"])
		icn=eduapp["icon"]
		if len(icn)>0:
			appicon=self.core.appstream.Icon()
			appicon.set_kind(self.core.appstream.IconKind.REMOTE)
			appicon.set_name(os.path.basename(icn))
			appicon.set_url(icn)
			app.add_icon(appicon)
		for cat in eduapp["categories"]:
			app.add_category(cat)
		if eduapp["auth"].lower().startswith("autori")==False:
			app.add_quirk(self.core.appstream.AppQuirk.NOT_LAUNCHABLE)
		else:
			app.add_quirk(self.core.appstream.AppQuirk.DEVELOPER_VERIFIED)
		return(app)
	#def _processApp

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		eduApps=self._getAppsEduCatalogue()
		rawcontent=self._getRawContent()
		fxml=os.path.join(self.cache,"appsedu.xml")
		if self._chkNeedUpdate(rawcontent)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			self._debug("Loaded {} from eduapps".format(len(eduApps)))
			for eduapp in eduApps:
				if "sistema" in eduapp["auth"].lower() or "coordinada" in eduapp["auth"].lower():
					continue
				store.add_app(self._processApp(eduapp))
			self.core._toFile(store,fxml)
		return(store)
	#def getAppstreamData
