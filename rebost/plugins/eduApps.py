#!/usr/bin/python3
#########
##
# THIS SCRIPT TRIES TO MAP EDUAPPS WITH REAL APPS
# IT'S A BEST EFFORT. ** RESULTS MUST BE REVISITED **
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

def _fetchCatalogue():
	content=''
	req=Request(EDUAPPS_URL, headers={'User-Agent':'Mozilla/5.0'})
	try:
		with urllib.request.urlopen(req,timeout=10) as f:
			content=(f.read().decode('utf-8'))
	except Exception as e:
		print("Couldn't fetch {}".format(EDUAPPS_URL))
		print("{}".format(e))
	return(content)

	for app in includeApps:
		print(app)
	for app in notFound:
		print(app)

regex=re.compile("[^\\w -]")
if __name__=="__main__":
	processEduApps()
