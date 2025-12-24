#!/usr/bin/env python3
import os,subprocess
import json,time
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
import hashlib
from bs4 import BeautifulSoup as bs

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
EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"

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
		fxml=os.path.join(self.cache,"appsedu.map")
		if os.path.isdir(os.path.dirname(fxml)):
			with open(fxml,"w") as f:
				f.write(json.dumps(mapFixes,indent=4))
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
		columnNameHref=None
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
				columnNameHref=column.find_all("a",href=True)
				columnName=column.text
			if (column.attrs["class"][0]=="column-5"):
				columnCats=column.text
			if (column.attrs["class"][0]=="column-7"):
				columnAuth=column.text
			if (column.attrs["class"][0]=="column-8"):
				#Discard the zero: tag
				columnPkgName=column.text.replace("zero:","")
				columnPkgName=columnPkgName.lower().removesuffix("-lliurex")
				columnPkgName=columnPkgName.lower().removesuffix("-appimage")
				columnPkgName=columnPkgName.lower().removesuffix("-snap")
				if len(columnCats.strip())>0:
					full=True
			if full==True:
				for data in columnNameHref:
					infopage=data["href"]
					candidate=os.path.basename(infopage.strip("/"))
				if candidate:
					candidate=candidate.lower().removesuffix("-lliurex").removesuffix("-appimage")
					if columnIcon==None:
						self._debug("NO ICON FOR {}".format(candidate))
						continue
					pkgIcon=columnIcon["src"]
					if candidate:
						if candidate in mapFixes["nodisplay"] or columnPkgName in mapFixes["nodisplay"]:
							continue
						if candidate in mapFixes["aliases"] or columnPkgName in mapFixes["aliases"]:
							self._debug("Was {} -> {}".format(columnPkgName,mapFixes["aliases"].get(candidate,mapFixes["aliases"].get(columnPkgName))))
							columnPkgName=mapFixes["aliases"].get(candidate,mapFixes["aliases"].get(columnPkgName))
						if isinstance(columnPkgName,str)==False:
							columnPkgName=candidate
						elif columnPkgName=="":
							columnPkgName=candidate
						cats=[]
						#Categories must be mapped 'cause are translated
						for cat in columnCats.split(","):
							realCat=self._getRealCategory(cat.strip())
							if len(realCat)>0 and realCat not in cats:
								cats.append(realCat)
						eduApps.append({"app":columnPkgName,"name":columnName,"icon":pkgIcon,"auth":columnAuth,"categories":cats,"infopage":infopage})
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
		#Force update
		update=True
		return(update)
	#def _chkNeedUpdate

	def _processApp(self,eduapp):
		app=self.core.appstream.App()
		app.set_trust_flags(self.core.appstream.AppTrustFlags.COMPLETE)
		app.set_source_kind(self.core.appstream.FormatKind.UNKNOWN)
		app.set_kind(self.core.appstream.AppKind.DESKTOP)
		pkgname=eduapp.get("app","").strip()
		aliasname=eduapp.get("alias","").strip()
		if len(aliasname)==0:
			aliasname=eduapp["app"]
		app.set_id(aliasname)
		app.add_pkgname(aliasname)
		for l in self.core.langs:
			app.set_name(l,eduapp["name"])
			app.set_comment(l,eduapp["auth"])
			app.set_description(l,eduapp["auth"])
		app.add_keyword("C",pkgname)
		#Icon
		icn=eduapp["icon"]
		if len(icn)>0:
			appicon=self.core.appstream.Icon()
			appicon.set_kind(self.core.appstream.IconKind.REMOTE)
			appicon.set_name(os.path.basename(icn))
			appicon.set_url(icn)
			app.add_icon(appicon)
		for cat in eduapp["categories"]:
			app.add_category(cat)
		#Status
		if (eduapp["auth"].lower().startswith("preparan")==True) or ("valua" in eduapp["auth"].lower()):
			app.add_kudo("UNAVAILABLE")
		elif  ("assis" in eduapp["auth"].lower()) or ("asistida" in eduapp["auth"].lower()) or ("coordinada" in eduapp["auth"].lower()):
			app.add_kudo("ASSISTED")
		elif  "web" in eduapp["auth"].strip().lower():
			app.add_kudo("WEBAPP")
		elif eduapp["auth"].lower().startswith("autori")==False:
			app.add_kudo("BLOCKED")
		else:
			app.set_state(self.core.appstream.AppState.AVAILABLE)
		#Release
		release="Appsedu"
		apprelease=self.core.appstream.Release()
		apprelease.set_size(self.core.appstream.SizeKind.DOWNLOAD,1000)
		apprelease.set_timestamp(int(time.time()))
		apprelease.set_version(release)
		app.add_release(apprelease)
		app.set_origin("appsedu")
		app.add_keyword("C","appsedu")
		#URLs
		app.add_url(self.core.appstream.UrlKind.HOMEPAGE,eduapp["infopage"])
		return(app)
	#def _processApp

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		#store.set_version("1.0.4")
		store.set_origin("appsedu")
		eduApps=self._getAppsEduCatalogue()
		rawcontent=self._getRawContent()
		fxml=os.path.join(self.cache,"appsedu.xml")
		if self._chkNeedUpdate(rawcontent)==False:
			self._debug("Loading from cache")
			store=self.core._fromFile(store,fxml)
		if len(store.get_apps())==0:
			self._debug("Loaded {} from eduapps".format(len(eduApps)))
			for eduapp in eduApps:
				#Discard systemd and coordinated apps
				if "sistema" in eduapp["auth"].lower(): # or "coordinada" in eduapp["auth"].lower():
					continue
				#Discard retired apps
				if "retir" in eduapp["auth"].lower() or "withdraw" in eduapp["auth"].lower():
					continue
				store.add_app(self._processApp(eduapp))
			self.core._toFile(store,fxml)
		self._debug("Sending {}".format(len(store.get_apps())))
		return(store)
	#def getAppstreamData

	def refreshAppData(self,app):
		#appsedu has no states
		return(app)
#class engine
