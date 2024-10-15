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
import rebostHelper
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
import random
import gettext
from bs4 import BeautifulSoup as bs
import html2text
# wget https://portal.edu.gva.es/appsedu/aplicacions-lliurex/
EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"
EDUAPPS_MAP="/usr/share/rebost/lists.d/eduapps.map"
FCACHE=os.path.join("/tmp/.cache/rebost",os.environ.get("USER"),"eduapps.html")

def _debug(msg):
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
	ban=["lliurex","server","kde","gtk","gnome","extras","portable","runtime","app","flash"]
	tags=[]
	for rawtag in rawtags:
		for tag in rawtag.split(" "):
			if len(tag)>2:
				if tag not in ban:
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

def getAppsEduCatalogue():
	_debug("Fetching {}".format(EDUAPPS_URL))
	rawcontent=_fetchCatalogue()
	if _chkNeedUpdate(rawcontent)==False:
		_debug("Skip update")
		#return([])
	bscontent=bs(rawcontent,"html.parser")
	appInfo=bscontent.find_all("td",["column-1","column-2","column-5","column-7"])
	eduApps=[]
	candidate=None
	columnAuth=None
	columnName=None
	columnCats=None
	columnIcon=None
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
			#Some apps should be hidden as are pure system apps (drkonqui...)
			#or apps included within another (kde-connect related stuff...)
			#or for some other reason (xterm..)
			#The 1st approach is based on category and authorizaton status
			#but there're many apps misscatalogued so disable it ATM
			#if columnAuth.lower().endswith("sistema"):
			#	if "utili" in columnCats.lower():
			#		columnAuth=None
			#		columnName=None
			#		columnIcon=None
			#		continue
			full=True
		if full==True:
			for data in columnName:
				href=data["href"]
				candidate=os.path.basename(href.strip("/"))
			if candidate:
				if columnIcon==None:
					print("NO ICON FOR {}".format(candidate))
					continue
				pkgIcon=columnIcon["src"]
				if candidate:
					eduApps.append({"app":candidate,"icon":pkgIcon,"auth":columnAuth})
					candidate=None
			columnAuth=None
			columnName=None
			columnIcon=None
	return(eduApps)
#def getAppsEduCatalogue

regex=re.compile("[^\\w -]")
#if __name__=="__main__":
#	processEduApps()
