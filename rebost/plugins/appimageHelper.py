#!/usr/bin/env python3
import os,stat
import json
import re
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
import random
import gettext
import threading
import shutil
import rebostHelper
from queue import Queue
import html2text
import hashlib
from bs4 import BeautifulSoup

class appimageHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		self.enabled=True
		self.packagekind="appimage"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=2
		self.store=None
		self.user=''
		dbCache="/tmp/.cache/rebost"
		if kwargs:
			self.user=kwargs.get('user','')
		#if self.user:
		self.appimageDir=os.path.join(os.getenv("HOME"),".local","bin")
		userCache=os.path.join(os.getenv("HOME"),".cache","rebost")
		#else:
		#	self.appimageDir="/opt/appimages"
		#	userCache=dbCache
		self.iconDir=os.path.join(userCache,"icons")
		self.wrkDir=os.path.join(userCache,"xml","appimage")
		for d in [self.wrkDir,self.iconDir]:
			if not os.path.isdir(d):
				os.makedirs(d)
				os.chmod(d, 0o0777)
		self.repos={'appimagehub':{'type':'json','url':'https://appimage.github.io/feed.json','url_info':''}}
		self.queue=Queue(maxsize=0)
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER",""))
		if os.path.exists(self.rebostCache)==False:
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","ai.lu")
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)
	#def setDebugEnabled(self,enable=True):

	def _debug(self,msg):
		if self.dbg:
			dbg="appimage: {}".format(msg)
			rebostHelper._debug(dbg)
	 #def _debug
	
	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)
	#def execute

	def _loadStore(self):
		action="load"
		searchDirs=self._searchdirsForAppimages()
		self._get_bundles_catalogue(searchDirs)
	
	def _get_bundles_catalogue(self,searchDirs=[]):
		applist=[]
		appdict={}
		all_apps=[]
		err=0
		msg=""
		#outdir=self.cache_xmls
		#Load repos
		self._debug("Loading store")
		for repo_name,repo_info in self.repos.items():
			appimageJson=self._fetch_repo(repo_info['url'])
			update=self._chkNeedUpdate(appimageJson,repo_name)
			if update:
				if appimageJson and repo_info.get("type","")=='json':
					self._process_appimage_json(appimageJson,repo_name,searchDirs=searchDirs)
					updateFile=self.lastUpdate.replace("ai","ai_{}".format(repo_name))
					appMd5=hashlib.md5(appimageJson.encode("utf-8")).hexdigest()
					with open(updateFile,'w') as f:
						f.write(appMd5)
				else:
					err=6
					msg="Couldn't fetch %s"%repo_info['url']
			else:
				self._debug("Skip update")
		return (err,msg)
	
	def _chkNeedUpdate(self,appimageJson,repo_name):
		update=True
		appMd5=""
		lastUpdate=""
		updateFile=self.lastUpdate.replace("ai","ai_{}".format(repo_name))
		if os.path.isfile(updateFile)==False:
			if os.path.isdir(os.path.dirname(updateFile))==False:
				os.makedirs(os.path.dirname(updateFile))
		else:
			fcontent=""
			with open(updateFile,'r') as f:
				lastUpdate=f.read()
			appMd5=hashlib.md5(appimageJson.encode("utf-8")).hexdigest()
			if appMd5==lastUpdate:
				update=False
		return(update)
	#def _chkNeedUpdate

	def _fetch_repo(self,repo):
		self._debug("Fetching {}".format(repo))
		content=''
		req=Request(repo, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urllib.request.urlopen(req,timeout=3) as f:
				content=(f.read().decode('utf-8'))
		except Exception as e:
			print("Couldn't fetch {}".format(repo))
			print("{}".format(e))
		return(content)
	#def _fetch_repo
	
	def _process_appimage_json(self,data,repo,searchDirs=[]):
		appList=[]
		thlist=[]
		if data:
			try:
				json_data=json.loads(data)
			except:
				json_data={}
			applist=json_data.get('items',[])
			maxconnections = 15
			random_applist = list(applist)
			random.shuffle(random_applist)
			semaphore = threading.BoundedSemaphore(value=maxconnections)
			#for appimage in applist:
			while applist:
				appimage=applist.pop(0)
				th=threading.Thread(target=self._th_process_appimage,args=(appimage,searchDirs,semaphore))
				th.start()
				thlist.append(th)
			for th in thlist:
				th.join(1)
		self._debug("PKG loaded")
		pkgList=[]
		while self.queue.empty()==False:
			pkgList.append(self.queue.get())
		rebostHelper.rebostPkgList_to_sqlite(pkgList,'appimage.db')
		self._debug("SQL loaded")
		return(applist)
	#_process_appimage_json
	
	def _th_process_appimage(self,appimage,searchDirs,semaphore):
		semaphore.acquire()
		appinfo=None
		if appimage.get('links'):
			appinfo=self.load_json_appinfo(appimage,searchDirs=searchDirs)
		  #  rebostHelper.rebostPkgList_to_xml([appinfo],'/tmp/.cache/rebost/xml/appimage/appimage.xml')
			#rebostHelper.rebostPkg_to_sqlite(appinfo,'appimage.db')
			self.queue.put(appinfo)
		semaphore.release()
		#def _th_process_appimage

	def load_json_appinfo(self,appimage,download=False,searchDirs=[]):
		rebostpkg=rebostHelper.rebostPkg()
		rebostpkg['name']=appimage['name'].strip()
		rebostpkg['pkgname']=rebostpkg['name'].lower()#.replace("_","-")
		rebostpkg['id']="io.appimage.{}".format(rebostpkg['name'])
		rebostpkg['license']=appimage.get('license','')
		if not rebostpkg.get('license'):
			rebostpkg['license']=''
		description=appimage.get('description','')
		if description:
			if isinstance(description,dict):
				for lang in description.keys():
					rebostpkg['description']=description
			else:
				rebostpkg['description']=description
			summary=".".join(description.split(".")[0:2])
			summary=" ".join(summary.split(" ")[0:8])
			summary=html2text.html2text(summary)
			rebostpkg['summary']=summary
		else:
			rebostpkg['summary']='Appimage of {}'.format(rebostpkg["name"])
			rebostpkg['description']='Appimage of {}'.format(rebostpkg["name"])
		rebostpkg['categories']=appimage.get('categories',[])
		if isinstance(rebostpkg['categories'],list)==False:	
			rebostpkg['categories']=[]
		icons=appimage.get('icons','')
		rebostpkg['icon']=appimage.get('icon','')
		if rebostpkg['icon']:# and download:
			if not rebostpkg['icon'].startswith("http"):
				rebostpkg['icon']="https://appimage.github.io/database/{}".format(rebostpkg['icon'])
		elif icons:
			#self._debug("Loading icon %s"%appimage['icons'])
			rebostpkg['icon']="https://appimage.github.io/database/{}".format(icons[0])
				#appinfo['icon']=icons[0]
		rebostpkg['screenshots']=appimage.get('screenshots',[])
		if rebostpkg['screenshots']:
			scrArray=[]
			for scr in rebostpkg['screenshots']:
				scrArray.append("https://appimage.github.io/database/{}".format(scr))
			rebostpkg["screenshots"]=scrArray
		links=appimage.get('links')
		installerurl=''
		version=""
		while links:
			link=links.pop(0)
			if link.get('url') and link.get('type','').lower()=='download' and download:
				installerUrl=self._get_releases(link['url'])
				if installerUrl.split('/')>2:
					version=installerUrl.split('/')[-2]
					rebostpkg['versions']['appimage']="{}".format(version)
				else:
					rebostpkg['versions']['appimage']="**"
			elif download==False:
				installerUrl=link['url']
			else:
				rebostpkg['versions']['appimage']="**"
		state="available"
		if os.path.isfile(os.path.join(self.appimageDir,"{}.appimage".format(rebostpkg['pkgname']))):
			rebostpkg['state']['appimage']="0"
		else:
			rebostpkg['state']['appimage']="1"
			for userDir in searchDirs:
				apps=[app.lower() for app in os.listdir(userDir)]
				if "{}.appimage".format(rebostpkg['pkgname']) in apps:
					rebostpkg['state']['appimage']="0"
					break
		if rebostpkg['state']['appimage']=="0":
			rows=rebostHelper.get_table_state(rebostpkg['pkgname'],'appimage')
			for row in rows:
				if row[-1]=="0":
					rebostpkg['installed']['appimage']=row[2]
				elif row[-1]=="1":
					rebostpkg['installed']['appimage']=""
				
		rebostpkg['bundle'].update({'appimage':"{}".format(installerUrl)})
		appimage['authors']=appimage.get('authors','')
		for author in appimage['authors']:
			if author.get('url',''):
				#self._debug("Author: %s"%author['url'])
				rebostpkg['homepage']=author['url']
		if not appimage['authors']:
			rebostpkg['homepage']='/'.join(rebostpkg['installerUrl'].split('/')[0:-1])
		return (rebostpkg)
	#def load_json_appinfo

	def _searchdirsForAppimages(self):
		#Appimages could be installed on any home available
		#In order to get installed status it's needed to scan users
		searchDirs=[]
		for user in os.listdir("/home"):
			binDir=os.path.join("/home",user,".local/bin")
			if os.path.isdir(binDir):
				apps=[b.lower() for b in os.listdir(binDir)]
				for app in apps:
					if ".appimage" in app:
						searchDirs.append(binDir)
		return (searchDirs)
	#def _searchdirsForAppimages

	def fillData(self,rebostPkg):
		if not isinstance(rebostPkg,dict):
			try:
				rebostPkg=json.loads(rebostPkg)
			except Exception as e:
				self._debug(e)
				self._debug(rebostPkg)
				return(rebostPkg)
		self._debug("Filling data for {}".format(rebostPkg.get('name')))
		bundle=rebostPkg['bundle'].get('appimage','')
		self._debug("Base URL {}".format(bundle))
		installerUrl=self._get_releases(bundle)

		version=""
		splittedUrl=installerUrl.split('/')
		if "releases" in installerUrl:
			if splittedUrl[-2].startswith("v"):
				version=splittedUrl[-2].replace("v","")
			elif splittedUrl[-2].replace(".","").isnumeric():
				version=splittedUrl[-2]

		if version=="" and  len(splittedUrl)>2: 
			self._debug("Installer {}".format(installerUrl))
			pkgname=installerUrl.split('/')[-1]
			pkgname=".".join(pkgname.split(".")[:-1])
			if len(pkgname.split("-"))>1:
				version=""
				for item in pkgname.split("-"):
					if item.replace("_","").replace(".","").isalpha():
						continue
					version=item
					break
				if version=="":
					version=pkgname.split("-")[1] 
			elif len(pkgname.split("."))>1:
				version=""
				for i in pkgname.split("."):
					if i.isnumeric():
						version+="{}.".format(i)
				version=version[:-1]
		if version=="":
			version="0.1"
		rebostPkg['versions'].update({'appimage':"{}".format(version)})
		rebostPkg['bundle'].update({'appimage':"{}".format(installerUrl)})
		if rebostPkg.get('icon','')!='' and not os.path.isfile(rebostPkg.get('icon')):
			rebostPkg['icon']=self._download_file(rebostPkg['icon'],rebostPkg['name'],self.iconDir)
		return (json.dumps(rebostPkg))

	def _get_releases(self,baseUrl):
		releases=[""]
		releases_page=''
		#self._debug("Info url: %s"%app_info['installerUrl'])
		url_source=""
		if 'github' in baseUrl:
			releases_page="https://github.com"
		if 'gitlab' in baseUrl:
			releases_page="https://gitlab.com"
		if 'opensuse' in baseUrl.lower():
			releases_page=""
			url_source="opensuse"
#		   app_info['installerUrl']=app_info['installerUrl']+"/download"

		self._debug("URL Source {}".format(url_source))
		self._debug("Releases Page {}".format(releases_page))
		if (url_source or releases_page) and not baseUrl.lower().endswith(".appimage"):
			self._debug("base Url: {}".format(baseUrl))
			content=''
			baseContent=''
			try:
				with urllib.request.urlopen(baseUrl) as f:
					baseContent=f.read().decode('utf-8')
			except Exception as e:
				self._debug("baseUrl UTF-8 failed")
			if baseContent!='':
				soup=BeautifulSoup(baseContent,"html.parser")
				assetUrl=self._scrapExpandedAssets(soup)
				try:
					with urllib.request.urlopen(assetUrl) as g:
						content=g.read().decode('utf-8')
				except:
					self._debug("assetUrl UTF-8 failed")
				soup=BeautifulSoup(content,"html.parser")
				package_a=soup.findAll('a', attrs={ "href" : re.compile(r'.*\.[aA]pp[iI]mage$')})
				for package_data in package_a:
					if url_source=="opensuse":
						package_name=package_data.findAll('a', attrs={"class" : "mirrorbrain-btn"})
					else:
						package_name=package_data.findAll('strong', attrs={ "class" : "pl-1"})
					package_link=package_data['href']
					#self._debug("Link: {}".format(package_link))
					#self._debug("Rel: {}".format(releases_page))
					#self._debug("Source: {}".format(url_source))
					if releases_page or url_source:
						package_link=releases_page+package_link
						self._debug("Link: {}".format(package_link))
						#if baseUrl in package_link:
						if package_link.lower().endswith(".appimage"):
							if url_source=="opensuse":
								releases.append("https://download.opensuse.org{}".format(package_link))
							else:
								releases.append(package_link)
		if releases==[]:
			releases=[baseUrl]
		self._debug(releases)
		rel=''
		releases.sort(reverse=True)
		for release in releases:
			if release.startswith("http"):
				rel=release
				break
		self._debug("Selected url: {}".format(rel))
		return rel

	def _scrapExpandedAssets(self,soup):
		assetUrl=""
		assets=soup.findAll('include-fragment', attrs={ "src" : re.compile(r'.*expanded_assets.*')})
		if len(assets)>0:
			assetUrl=assets[0]['src']
		return(assetUrl)
	#def _scrapExpandedAssets
	
	def _download_file(self,url,app_name,dest_dir):
		#self._debug("Downloading to %s"%self.iconDir)
		target_file=dest_dir+'/'+app_name.strip()+".png"
		self._debug("Orig url: {}".format(url))
		if not url.startswith('http'):
			url="https://appimage.github.io/database/%s"%url
		if not os.path.isdir(self.iconDir):
		   os.makedirs(self.iconDir)
		if not os.path.isfile(target_file):
		   self._debug("Downloading %s to %s"%(url,target_file))
		   try:
			   with urllib.request.urlopen(url) as response, open(target_file, 'wb') as out_file:
				   bf=16*1024
				   acumbf=0
				   file_size=int(response.info()['Content-Length'])
				   while True:
					   if acumbf>=file_size:
						   break
					   shutil.copyfileobj(response, out_file,bf)
					   acumbf=acumbf+bf
			   st = os.stat(target_file)
		   except Exception as e:
			   self._debug("Unable to download %s"%url)
			   self._debug("Reason: %s"%e)
			   target_file=''
		else:
		   self._debug("{} already downloaded".format(self.iconDir))
		return(target_file)
	#def _download_file

def main():
	obj=appimageHelper()
	return (obj)

