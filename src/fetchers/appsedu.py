#!/usr/bin/env python3
import os
from urllib.request import Request,urlopen
import concurrent.futures as Futures
import hashlib
from bs4 import BeautifulSoup as bs
import gi
from gi.repository import Gio
gi.require_version('AppStream', '1.0')
from gi.repository import AppStream as appstream

EDUAPPS_URL="https://portal.edu.gva.es/appsedu/aplicacions-lliurex/"

i18n={'àudio':"Audio",
	'audio':"Audio",
	'cad':"Engineering",
	'electrònica':"Electronics", 
	'electronica':"Electronics", 
	'ciencies':"Science",
	'ciències':"Science",
	'disseny':"Engineering",
	'enginyeria':"Engineering",
	'física':"Physics",
	'fisica':"Physics",
	'fotografia':"Photography", 
	'gamificació':"Education",
	'gamificacio':"Education",
	'geografia':"Geography",
	'gràfics':"Graphics",
	'grafics':"Graphics",
	'informàtica':"ComputerScience",
	'informatica':"ComputerScience",
	'ingenieria':"Engineering",
	'intel·ligència Artificial':"ArtificialIntelligence", 
	'matemàtiques':"Math", 
	'matematiques':"Math", 
	'multimèdia':"AudioVideo", 
	'música':"Music",
	'musica':"Music",
	'ofimàtica':"Office",
	'ofimatica':"Office",
	'presentacions':"Presentation",
	'programació':"Development", 
	'programacio':"Development", 
	'química':"Chemistry",
	'quimica':"Chemistry",
	'robótica':"Robotics", 
	'robotica':"Robotics", 
	'tecnologia':"Robotics", 
	'tecnología':"Robotics", 
	'utilitats':"Utility", 
	'vídeo':"Video",
	'video':"Video"
	}

class fetcher:
	def __init__(self,*args,**kwargs):
		self.name="appsedu"
		self.dbg=True
		#self.cache=os.path.join(self.core.CACHE,"raw")
		self.cache="/tmp/cache"
		self.cacheApps=os.path.join(self.cache,"metainfo")
		self.store=appstream.Metadata()
		self.thExecutor=Futures.ThreadPoolExecutor(max_workers=4)
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("{0}: {1}".format(self.name,msg))
	#def _debug

	def _fetchUrl(self,url):
		content=''
		req=Request(url, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urlopen(req,timeout=2) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			self._debug("Couldn't fetch {}".format(url))
			self._debug(e)
		return(content)
	#def _fetchUrl

	def _writeCache(self,content,fpath):
		ret=False
		if os.path.exists(fpath)==False:
			try:
				dpath=os.path.dirname(fpath)
				if os.path.exists(dpath)==False:
					os.makedirs(dpath)
			except:
				pass
		try:
			with open(fpath,"w") as f:
				f.write(rawcontent)
				ret=True
		except:
			pass
		return(ret)
	#def _writeCache

	def _getAppUrls(self,content):
		bscontent=bs(content,"html.parser")
		appRawUrls=bscontent.find_all("td",["column-2"])
		appUrls=[]
		for column in appRawUrls:
			link=column.find_all("a",href=True)
			for item in link:
				appUrls.append(item["href"])
		return(appUrls)
	#def _getAppUrls

	def _getAvailability(self,bscontent):
		availability=bscontent.find("div",["acf-view__estat_val-choice acf-view__choice"])
		if availability!=None:
			availability=availability.text.strip()
		else:
			availability=""
		return(availability)
	#def _getAvailability

	def _getKind(self,bscontent):
		availability=self._getAvailability(bscontent).lower()
		if availability.startswith("disponible") and availability.endswith("web"):
			kind=appstream.ComponentKind.WEB_APP
		elif availability.startswith("aut") and availability.endswith("botiga"):
			kind=appstream.ComponentKind.DESKTOP_APP
		else:
			kind=appstream.ComponentKind.UNKNOWN
		return(kind)
	#def _getKind

	def _getId(self,bscontent):
		cid=""
		appId=bscontent.find("a",class_="boto-blau",href=True)
		if appId!=None:
			cid=appId["href"].split("://")[-1].strip()
		return(cid)
	#def _getId

	def _getRelease(self,bscontent):
		release=appstream.Release()
		return(release)
	#def _getRelease(self,bscontent):

	def _getName(self,bscontent):
		name=""
		appName=bscontent.find("h1",itemprop="headline")
		if appName!=None:
			name=appName.text
		return(name)
	#def _getDesc

	def _getDesc(self,bscontent):
		desc=""
		appDesc=bscontent.find("div",["acf-view__descripcio-field"])
		if appDesc!=None:
			desc=appDesc.text
		return(desc)
	#def _getDesc

	def _getSummary(self,description):
		summary=description.split(".")[0].strip()
		if summary.count(" ")>12:
			summary=" ".join(summary.split(" ")[:11]).strip()+"..."
		if len(summary)>100:
			summary=summary[:99]+"..."
		return(summary)
	#def _getSummary

	def _getCategories(self,bscontent):
		categories=[]
		cats=bscontent.find_all("div",["acf-view__categoria_val-choice acf-view__choice"])
		for cat in cats:
			cat=cat.text.strip()
			realCat=i18n.get(cat.lower())
			if realCat!=None:
				categories.append(realCat)
		if len(categories)==0:
			categories.append("Utility")
		return(categories)
	#def _getCategories

	def _getIcon(self,bscontent):
		icon=appstream.Icon()
		appIcon=bscontent.find("img",class_="acf-view__image")
		if appIcon!=None:
			iconUrl=appIcon.get("src","")
			icon.set_kind(appstream.IconKind.REMOTE)
			icon.set_url(iconUrl)
		return(icon)
	#def _getIcon

	def _getUrls(self,bscontent):
		urls=[]
		urlEditor=bscontent.find("a",["acf-view__url_editor-link acf-view__link"],href=True)
		if urlEditor!=None:
			url=urlEditor.get("href","")
			urls.append((appstream.UrlKind.HOMEPAGE,url))
		urlsExtra=bscontent.find("div",["acf-view__urls_externes_val-field acf-view__field"])
		if urlsExtra!=None:
			for li in urlsExtra.find_all("li"):
				if "privaci" in li.text.lower():
					ref=li.find("a",href=True)
					urls.append((appstream.UrlKind.FAQ,ref.get("href","")))
				if "legal" in li.text.lower():
					ref=li.find("a",href=True)
					urls.append((appstream.UrlKind.CONTACT,ref.get("href","")))
				if "condicion" in li.text.lower():
					ref=li.find("a",href=True)
					urls.append((appstream.UrlKind.HELP,ref.get("href","")))
		return(urls)
	#def _getUrls

	def _getRating(self,bscontent):
		rating=appstream.ContentRating()
		attr="social-info"
		value=appstream.ContentRatingValue.MILD
		auths=bscontent.find_all("div",["acf-view__usuaris_autoritzats_val-choice acf-view__choice"])
		for auth in auths:
			if auth.text.strip().lower()=="alumnat":
				value=appstream.ContentRatingValue.NONE
				break
		rating.set_value(attr,value)
		return(rating)
	#def _getRating

	def _generateAppstreamForApp(self,future):
		url,content=future.result()
		if len(content)>0:
			bscontent=bs(content,"html.parser")
			app=appstream.Component()
			app.set_kind(self._getKind(bscontent))
			self._getAvailability(bscontent)
			app.set_origin("appsedu")
			app.set_priority(100)
			app.set_id(self._getId(bscontent))
			app.set_name(self._getName(bscontent),"C")
			app.set_description(self._getDesc(bscontent))
			app.set_summary(self._getSummary(app.get_description()),"C")
			for cat in self._getCategories(bscontent):
				app.add_category(cat)
			app.add_icon(self._getIcon(bscontent))
			app.add_url(appstream.UrlKind.UNKNOWN,url)
			for urls in self._getUrls(bscontent):
				urlK,urlD=urls
				app.add_url(urlK,urlD)
			app.add_content_rating(self._getRating(bscontent))
			self.store.add_component(app)
		self.jobs-=1
		if self.jobs==0:
			a=self.store.components_to_catalog(appstream.FormatKind.XML)
			with open("/tmp/appsedu.dep11","w") as f:
				f.write(a)
	#def _generateAppstreamForApp

	def _fetchApp(self,url):
		self.jobs+=1
		content=self._fetchUrl(url)
		url=url.strip().removesuffix("/")
		fappstream=os.path.basename(url).replace(".html","")
		fpath=os.path.join(self.cache,"{}.html".format(fappstream))
		self._writeCache(content,fpath)
		return(url,content)

	def fetchCatalogue(self):
		content=self._fetchUrl(EDUAPPS_URL)
		fpath=os.path.join(self.cache,"appsedu.raw")
		self._writeCache(content,fpath)
		appUrls=self._getAppUrls(content)
		self.jobs=0
		if len(appUrls)>0:
			for url in appUrls:
				init=self.thExecutor.submit(self._fetchApp,url)
				init.add_done_callback(self._generateAppstreamForApp)
	#def fetchCatalogue
