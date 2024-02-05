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
import html2text
# wget https://portal.edu.gva.es/appsedu/aplicacions-lliurex/
EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"
FILTER="/usr/share/rebost/lists.d/include/apps/eduapps.conf"

class eduHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.enabled=False
		self.packagekind=""
		self.actions=["load"]
		#self.postAutostartActions=["load"]
		self.regex=re.compile("[^\\w -]")
		self.priority=1
		self.lastUpdate="/usr/share/rebost/tmp/ea.lu"
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))

	def _debug(self,msg):
		if self.dbg:
			dbg="eduApps: {}".format(msg)
			rebostHelper._debug(dbg)
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
		searchDict=self._generateTags(eduApps)
		print("WAIT 5")
		time.sleep(5)
		self.rebost=store.client()
		self._processApps(searchDict)
	#def processEduApps

	def _getEduApps(self):
		self._debug("Fetching {}".format(EDUAPPS_URL))
		rawcontent=self._fetchCatalogue()
		bscontent=bs(rawcontent,"html.parser")
		b=bscontent.find_all("td",["column-2","column-7"])
		eduApps=[]
		candidate=None
		for i in b:
			c=i.find("a")
			#print(c)
			if c:
				if c.text.lower()!="lliurex":
					candidate=c.text
					continue
			c=i.text
			if c.lower().startswith("autori"):
				if candidate:
					eduApps.append(candidate)
					candidate=None
			else:
				print("Reject: {}".format(candidate))
		return(eduApps)
	#def getEduApps

	def _fetchCatalogue(self):
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

	def _generateTags(self,eduapps):
		tags={}
		for app in eduapps:
			maintags=self._extractTags(app)
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

	def _extractTags(self,app):
		raw=self.regex.sub("-",app)
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
					found=True
					end=True
					break
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
		#try:
		#	with open(FILTER,"w") as f:
		#		f.write("\n".join(includeApps))
		#except PermissionError as e:
		#	print("Error writing {}".format(FILTER))
		#	print(e)
	#def _processApps

def main():
	obj=eduHelper()
	return (obj)

