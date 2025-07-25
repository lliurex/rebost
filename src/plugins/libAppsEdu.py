#!/usr/bin/python3
#########
##
# THIS SCRIPT TRIES TO MAP EDUAPPS WITH REAL APPS
# IT'S A BEST EFFORT. ** RESULTS MUST BE REVISITED **
# IT ALSO MANAGES CACHE AND CATALOGUE DOWNLOAD
##
#######
import time,os
import json
import re
from rebost import store
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
import random
import gettext
from bs4 import BeautifulSoup as bs
import html2text
# wget https://portal.edu.gva.es/appsedu/aplicacions-lliurex/
EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"
EDUAPPS_MAP="/usr/share/rebost-data/lists.d/llx25/eduapps.map"
EDUAPPS_MAP_URL="https://github.com/lliurex/rebost-data/raw/refs/heads/master/lists.d/llx25/eduapps.map"
FCACHE=os.path.join("/tmp/.cache/rebost",os.environ.get("USER"),"eduapps.html")
EDUAPPS_RAW=os.path.join(os.path.dirname(FCACHE),".eduapps.raw")
DEBUG=False

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

def _debug(msg):
	if DEBUG==True:
		print("eduApps: {}".format(msg))

def processEduApps():
	if os.path.exists(EDUAPPS_MAP):
		os.unlink(EDUAPPS_MAP)
	rebost=store.client()
	eduApps=_getEduApps()
	searchDict=_generateTags(eduApps)
	_processApps(rebost,searchDict)
#def processEduApps

def _generateTags(eduapps):
	tags={}
	for app in eduapps:
		maintags=_extractTags(app)
		tags[app.lower()]={"tags":maintags}
		extratags=[]
		extratag=""
		if len(maintags)>1:
			for sep in ["-","","_"]:
				extratags.append(sep.join(maintags))
			for i in range(len(maintags)):
				if len(extratag):
					for sep in ["-","","_"]:
						extratags.append("{0}{1}{2}".format(extratag,sep,maintags[i]))
					extratag=""
				extratag=maintags[i]
		tags[app.lower()].update({"extratags":extratags})
	return(tags)
#def _generateTags

def _extractTags(app):
	raw=regex.sub("-",app)
	rawtags=raw.lower().split("-")
	ban=["lliurex","server","kde","gtk","gnome","extras","portable","runtime","app","flash","qt"]
	tags=[]
	for rawtag in rawtags:
		for tag in rawtag.split(" "):
			if len(tag)>2:
				if tag.lower() not in ban:
					tags.append(tag.lower())
	return(tags)
#def _extractTags

def _processApps(rebost,searchDict):
	notFound=[]
	includeApps=[]
	mapApp={}
	for app,searchtags in searchDict.items():
		mapApp[app]=app
		tags=searchtags.get("tags",[])
		extratags=searchtags.get("extratags",[])
		found=False
		_debug("Search: {}".format(app))
		for tag in tags:
			_debug(" Tag: {}".format(tag))
			res=rebost.matchApp(tag)
			if len(res)>2:
				try:
					candidate=json.loads(json.loads(res)[0])
				except:
					print("Taking breath..")
					rebost.restart()
					rebost=store.client()
					res=rebost.matchApp(tag)
					candidate=json.loads(json.loads(res)[0])
				pkgname=candidate.get("pkgname")
				if pkgname not in includeApps:
					includeApps.append(pkgname)
					mapApp[app]=pkgname
				found=True
				break
		if found==False:
			for tag in extratags:
				time.sleep(0.2)
				_debug(" ExtraTag: {}".format(tag))
				res=rebost.matchApp(tag)
				if len(res)>2:
					candidate=json.loads(json.loads(res)[0])
					pkgname=candidate.get("pkgname")
					if pkgname not in includeApps:
						includeApps.append(pkgname)
						mapApp[app]=pkgname
					found=True
					break
		if found==False:
			notFound.append(app)
	if len(notFound)>0:
		(includeApps,notFound,mapApp)=_lazySearch(rebost,searchDict,includeApps,notFound,mapApp)
	if len(notFound)>0:
		print("Rest: {}".format(len(notFound)))
	print("Found: {}".format(includeApps))
	print("NotFound: {}".format(notFound))
	try:
		with open(EDUAPPS_MAP,"w") as f:
			json.dump(mapApp, f,ensure_ascii=True, indent=4, sort_keys=True)
	except PermissionError as e:
		print("Error writing {}".format(EDUAPPS_MAP))
		print(e)
	#rebost.restart()

def _lazySearch(rebost,searchDict,includeApps,pendingApps,mapApp):
	notFound=[]
	for app in pendingApps:
		searchtags=searchDict.get(app,{}).copy()
		tags=searchtags.get("tags",[])
		extratags=searchtags.get("extratags",[])
		found=False
		_debug("LazySearch: {}".format(app))
		for tag in tags:
			_debug(" LazyTag: {}".format(tag))
			res=rebost.searchApp(tag)
			if len(res)>2:
				candidate=json.loads(json.loads(res)[0])
				pkgname=candidate.get("pkgname")
				if pkgname not in includeApps:
					includeApps.append(pkgname)
					mapApp[app]=pkgname
				found=True
				break
		if found==False:
			for tag in extratags:
				_debug(" LazyExtraTag: {}".format(tag))
				res=rebost.searchApp(tag)
				if len(res)>2:
					candidate=json.loads(json.loads(res)[0])
					pkgname=candidate.get("pkgname")
					if pkgname not in includeApps:
						includeApps.append(pkgname)
						mapApp[app]=pkgname
					found=True
					break
		if found==False:
			notFound.append(app)
	return(includeApps,notFound,mapApp)

def _getEduApps():
	_debug("Fetching {}".format(EDUAPPS_URL))
	rawcontent=_fetchCatalogue()
	bscontent=bs(rawcontent,"html.parser")
	b=bscontent.find_all("td","column-2")
	eduApps=[]
	candidate=None
	for i in b:
		c=i.find("a")
		if c:
			href=c['href']
			candidate=os.path.basename(href.strip("/"))
		if candidate:
			eduApps.append(candidate)
			candidate=None
	return(eduApps)
#def getEduApps

def downloadCatalogue(url=EDUAPPS_URL):
	content=""
	req=Request(url, headers={'User-Agent':'Mozilla/5.0'})
	try:
		with urllib.request.urlopen(req,timeout=10) as f:
			content=(f.read().decode('utf-8'))
	except Exception as e:
		print("Couldn't fetch {}".format(url))
		print("{}".format(e))
	return(content)
#def downloadCatalogue

def _fetchCatalogue(url=""):
	if len(url)==0:
		url=EDUAPPS_URL
	content=downloadCatalogue(url)
	if not os.path.exists(FCACHE):
		if len(content)>0:
			_writeCache(content)
	print("Read catalogue from {}".format(FCACHE))
	if len(content)>0:
		fcontent=_readCache()
		if content!=fcontent:
			_writeCache(content)
	return(content)
#def _fetchCatalogue

def _writeCache(content):
	print("Writing cache...")
	with open(FCACHE,"w") as f:
		f.write(content)
#def _writeCache

def _readCache():
	fcontent=""
	if os.path.exists(FCACHE):
		with open(FCACHE,"r") as f:
			fcontent=f.read()
	return(fcontent)
#def _readCache

def _chkNeedUpdate(urlcontent):
	update=True
	return(update)
#def _chkNeedUpdate

def getRawContent():
	rawcontent=""
	if os.path.exists(EDUAPPS_RAW):
		with open(EDUAPPS_RAW,"r") as f:
			rawcontent=f.read()
	return(rawcontent)
#def getRawContent

def _getAppseduMapFixes():
	mapFixes={"nodisplay":[],"alias":{}}
	if os.path.exists(EDUAPPS_MAP):
		with open(EDUAPPS_MAP,"r") as f:
			mapFixes=json.loads(f.read())
	mapFixesUrlContent=downloadCatalogue(EDUAPPS_MAP_URL)
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

def getAppsEduCatalogue():
	_debug("Fetching {}".format(EDUAPPS_URL))
	rawcontent=_fetchCatalogue()
	with open(EDUAPPS_RAW,"w") as f:
		f.write(rawcontent)
	if _chkNeedUpdate(rawcontent)==False:
		_debug("Skip update")
		#return([])
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
	mapFixes=_getAppseduMapFixes()
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
					_debug("NO ICON FOR {}".format(candidate))
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
						realCat=_getRealCategory(cat.strip())
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
#def getAppsEduCatalogue

def _getRealCategory(cat):
	cat=i18n.get(cat,cat)
	return(cat)
#def _getRealCategory


regex=re.compile("[^\\w -]")
#if __name__=="__main__":
#	processEduApps()
