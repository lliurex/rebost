#!/usr/bin/python3
#import rebostHelper
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
import rebostHelper
import hashlib
# wget https://portal.edu.gva.es/appsedu/aplicacions-lliurex/
EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"
FILTER="/usr/share/rebost/lists.d/include/apps/eduapps.conf"
MAP="/usr/share/rebost/lists.d/eduapps.map"

class eduHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		self.enabled=True
		self.packagekind=""
		self.actions=["load"]
		self.autostartActions=["load"]
		self.regex=re.compile("[^\\w -]")
		self.priority=1
		self.lastUpdate="/usr/share/rebost/tmp/eh.lu"
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))

	def _debug(self,msg):
		if self.dbg:
			dbg="eduapps: {}".format(msg)
			print(dbg)
	#def _debug

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)

	def _loadStore(self):
		if os.path.exists(FILTER):
			os.unlink(FILTER)
		eduApps=self._getEduApps()
		self._debug("Loaded {} from eduapps".format(len(eduApps)))
		rebostPkgList=[]
		for eduapp in eduApps:
			rebostPkgList.append(self._appToRebost(eduapp))
		self._debug("Sending {} to sqlite".format(len(rebostPkgList)))
		if len(rebostPkgList)>0:
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,"eduapps.db")
		#REM
		return
		searchDict=self._generateTags(eduApps)
		self.rebost=store.client()
		rebostpkglist=self._processApps(searchDict)
		rebostHelper.rebostToAppstream(rebostpkglist,"/tmp/eduapps.list")
	#def processEduApps

	def _chkNeedUpdate(self,urlcontent):
		update=True
		appMd5=hashlib.md5(urlcontent.encode("utf-8")).hexdigest()
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
		else:
			fcontent=""
			with open(self.lastUpdate,'r') as f:
				lastUpdate=f.read()
			if appMd5==lastUpdate:
				update=False
		with open(self.lastUpdate,'w') as f:
			f.write(appMd5)
		return(update)
	#def _chkNeedUpdate

	def _getEduApps(self):
		self._debug("Fetching {}".format(EDUAPPS_URL))
		rawcontent=self._fetchCatalogue()
		if self._chkNeedUpdate(rawcontent)==False:
			self._debug("Skip update")
			#return([])
		bscontent=bs(rawcontent,"html.parser")
		appInfo=bscontent.find_all("td",["column-1","column-2","column-7"])
		eduApps=[]
		candidate=None
		columnAuth=None
		columnName=None
		columnIcon=None
		for column in appInfo:
			full=False
			if (column.attrs["class"][0]=="column-1"):
				columnIcon=column.img
			if (column.attrs["class"][0]=="column-2"):
				columnName=column.find_all("a",href=True)
			if (column.attrs["class"][0]=="column-7"):
				columnAuth=column.text
				full=True
			if full==True:
				for data in columnName:
					href=data["href"]
					candidate=os.path.basename(href.strip("/"))
				if candidate:
			#		pkgIcon=""
			#		for data in columnIcon:
			#			pkgIcon=data["src"]
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
	#def getEduApps

	def _appToRebost(self,eduapp,getDetail=False):
		rebostPkg=rebostHelper.rebostPkg()
		appmap={}
		if os.path.isfile(MAP):
			with open(MAP,"r") as f:
				appmap=json.loads(f.read())
		app=eduapp["app"]
		pkgname=app
		if app in appmap:
			if app!=appmap[app]:
				rebostPkg["alias"]=appmap[app]
		rebostPkg["name"]=app.rstrip("-2")
		rebostPkg["pkgname"]=pkgname
		rebostPkg["id"]="gva.appsedu.{}".format(pkgname)
		rebostPkg["bundle"]={"eduapp":pkgname}
		rebostPkg["icon"]=eduapp["icon"]
		if eduapp["auth"].lower().startswith("autori")==False:
			self._debug("Set {} as FORBIDDEN".format(pkgname))
			rebostPkg["categories"].insert(0,"FORBIDDEN")
		if getDetail==True:
			appUrl=os.path.join("/".join(EDUAPPS_URL.split("/")[:-2]),eduapp)
			rawcontent=self._fetchCatalogue(appUrl)
			bscontent=bs(rawcontent,"html.parser")
			b=bscontent.find_all("div","entry-content")
			for i in b:
				img=i.find("img")
				if img:
					print("Image: {}".format(img["src"]))
					rebostPkg["icon"]=img["src"]
				rel=i.find("div","acf-view__versio-field acf-view__field")
				if rel:
					print("Release: {}".format(rel.text.strip()))
					rebostPkg["versions"]={"eduapp":rel.text.strip()}
					#rebostPkg["icon"]=img["src"]
				desc=i.find("div","acf-view__descripcio-field acf-view__field")
				if desc:
					print("Description: {}".format(desc.text.strip()))
					rebostPkg["description"]=desc.text.strip()
					summary=rebostPkg["description"].split(".")[0]
					rebostPkg['summary']=summary
				homepage=i.find("div","acf-view__url_editor-link acf-view__link")
				if homepage:
					print("Homepage: {}".format(homepage.text.strip()))
					rebostPkg["homepage"]=homepage.text.strip()
				auth=i.find("div","acf-view__estat_val-choice acf-view__choice")
				if auth:
					print("Auth: {}".format(auth.text.strip()))
				reject=i.find("div","acf-view__motiu_de_no_autoritzacio_val-choice acf-view__choice")
				if reject:
					print("Rejected by: {}".format(reject.text.strip()))
					rebostPkg["description"]+="****{}".format(reject.text.strip())
					rebostPkg["bundle"]={"eduapp":"banned"}
				cats=i.find("div","acf-view__categoria_val-choice acf-view__choice")
				if cats:
					print("Cats: {}".format(cats.text.strip()))
					rebostPkg["categories"]=cats.text.strip().split()

				#Without use
				groups=i.find("acf-view__usuaris_autoritzats_val-choice acf-view__choice")
				ident=i.find("acf-view__identitat_val-choice acf-view__choice")
				ambit=i.find("div","acf-view__ambit_educatiu_val-label acf-view__label")
			rebostPkg['description']=rebostHelper._sanitizeString(rebostPkg['description'],unescape=True)
			rebostPkg['summary']=rebostHelper._sanitizeString(rebostPkg['summary'])
			rebostPkg['name']=rebostHelper._sanitizeString(rebostPkg['name'])
		return(rebostPkg)
	#def _getAppDetail(self,eduapp):

	def _fetchCatalogue(self,url=""):
		if len(url)==0:
			url=EDUAPPS_URL
		content=''
		req=Request(url, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urllib.request.urlopen(req,timeout=10) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			print("Couldn't fetch {}".format(url))
			print("{}".format(e))
		return(content)
	#def _fetchCatalogue


	def _generateTags(self,eduapps):
		tags={}
		for app in eduapps:
			maintags=self._extractTags(app)
			tags[app.lower()]={"tags":maintags}
			extratags=[]
			extratag=""
			if len(maintags)>1:
				for i in range(len(maintags)):
					if len(extratag)>0:
						for sep in ["-","","_"]:
							compoundTag="{0}{1}{2}".format(extratag,sep,maintags[i])
							if compoundTag not in extratags:
								extratags.append(compoundTag)
						extratag=""
					extratag=maintags[i]
				for sep in ["-","","_"]:
					extratags.append(sep.join(maintags))
			tags[app.lower()].update({"extratags":extratags})
		return(tags)
	#def _generateTags

	def _extractTags(self,app):
		tags=[]
		raw=self.regex.sub("-",app).lower()
		rawtags=raw.lower().split("-")
		tags.append("".join(rawtags).replace(" ",""))
		ban=["lliurex","server","kde","gtk","gnome","extras","portable","runtime","app","flash"]
		for rawtag in rawtags:
			if len(rawtag)<=2:
				continue
			mtag=rawtag.replace(" ","-")
			if mtag not in tags:
				tags.append(mtag)
			for tag in rawtag.split(" "):
				tag=tag.strip().lower()
				if len(tag)>2:
					if tag not in ban and tag not in tags:
						tags.append(tag)
		return(tags)
	#def _extractTags

	def rebostQuery(self,app,searchtags):
		tags=searchtags.get("tags",[])
		extratags=searchtags.get("extratags",[])
		found=False
		self._debug("Search: {}".format(app))
		strict=False
		end=False
		rebostPkg={}
		while end==False:
			end=strict
			strict=not(strict)
			for tag in tags+extratags:
				self._debug(" Tag: {}".format(tag))
				rebostPkg=self._rebostQueryEduapp(tag,strict=strict)
				if len(rebostPkg.get("pkgname",""))>0:
					if rebostPkg["pkgname"] in tags or rebostPkg["pkgname"] in extratags or rebostPkg["pkgname"] in app.lower() or app.lower() in rebostPkg["pkgname"]:
						found=True
						end=True
						break
					#else:
					#	print("FIND: {}".format(rebostPkg["pkgname"]))
					#	print("DISCARD: {}".format(extratags))
					#	print("DISCARD: {}".format(tags))
					#	print("DISCARD: {}".format(app))
				time.sleep(0.1)
		return(rebostPkg)
	#def rebostQuery(self,app,strict=False):

	def _rebostQueryEduapp(self,eduapp,strict=False):
		rebostApp={}
		if strict==True:
			res=self.rebost.matchApp(eduapp)
		else:
			res=self.rebost.searchApp(eduapp)
		try:
			rebostApp=self._loadRes(res)
		except:
			print("Taking breath..")
			self.rebost.restart()
			res=query(eduapp)
			rebostApp=self._loadRes(res)
		pkgname=rebostApp.get("pkgname","")
		if strict==False and len(pkgname)==0:
			res=self.rebost.searchApp(eduapp)
			try:
				rebostApp=self._loadRes(res)
			except:
				print("Taking breath..")
				self.rebost.restart()
				if strict==True:
					res=self.rebost.matchApp(eduapp)
				else:
					res=self.rebost.searchApp(eduapp)
				rebostApp=self._loadRes(res)
		return(rebostApp)
	#def rebostQueryEduapp

	def _loadRes(self,res):
		candidate={}
		if len(res)>2:
			candidate=json.loads(json.loads(res)[0])
			pkgname=candidate.get("pkgname","")
		return(candidate)
	#def _loadRes(self,res):

	def _processApps(self,searchDict):
		notFound=[]
		includeApps=[]
		for app in searchDict:
			rebostPkg=self.rebostQuery(app,searchDict[app])
			if len(rebostPkg)>0:
				includeApps.append(rebostPkg)
			else:
				notFound.append(app)
		if len(notFound)>0:
			print("Rest: {}".format(len(notFound)))
		print("Found: {}".format(includeApps))
		print("NotFound: {}".format(notFound))
		rebostHelper.rebostToAppstream(includeApps)
		#Uncomment for filter creation
		#try:
		#	with open(FILTER,"w") as f:
		#		f.write("\n".join(includeApps))
		#except PermissionError as e:
		#	print("Error writing {}".format(FILTER))
		#	print(e)
		return(includeApps)
	#def _processApps

def main():
	obj=eduHelper()
	return (obj)

