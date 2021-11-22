#!/usr/bin/env python3
import os
import json
import re
import urllib
from urllib.request import Request
from urllib.request import urlretrieve
import random
import time
import datetime
import gettext
import threading
import shutil
from bs4 import BeautifulSoup
import tempfile
import rebostHelper
import subprocess
import logging
from queue import Queue
import html

class appimageHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.packagekind="appimage"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=1
		self.store=None
		self.user=''
		if kwargs:
			self.user=kwargs.get('user','')
		if self.user:
			self.appimageDir=os.getenv("HOME")+"/.local/bin"
		else:
			self.appimageDir="/opt/appimages"
		self.wrkDir="/tmp/.cache/rebost/xml/appimage"
		self.iconDir="/tmp/.cache/rebost/icons"
		self.repos={'appimagehub':{'type':'json','url':'https://appimage.github.io/feed.json','url_info':''}}
		self.queue=Queue(maxsize=0)
#		self._loadStore()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("appimage: %s"%str(msg))
	
	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)
	#def execute

	def _loadStore(self):
		action="load"
		self._get_bundles_catalogue()
	
	def _get_bundles_catalogue(self):
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
			if appimageJson and repo_info['type']=='json':
				self._process_appimage_json(appimageJson,repo_name)
			else:
				err=6
				msg="Couldn't fetch %s"%repo_info['url']
		return (err,msg)
	
	def _fetch_repo(self,repo):
		self._debug("Fetching {}".format(repo))
		content=''
		req=Request(repo, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urllib.request.urlopen(req) as f:
				content=(f.read().decode('utf-8'))
		except:
			print("Couldn't fetch %s"%repo)
		return(content)
	#def _fetch_repo
	
	def _process_appimage_json(self,data,search=''):
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
			for appimage in applist:
				#rebostPkg=self._process_appimage(appimage,search)
				#if rebostPkg:
					#applist.append(rebostPkg)
				th=threading.Thread(target=self._th_process_appimage,args=(appimage,semaphore))
				th.start()
				thlist.append(th)
			for th in thlist:
				th.join()
		self._debug("PKG loaded")
		pkgList=[]
		while not self.queue.empty():
			pkgList.append(self.queue.get())
		rebostHelper.rebostPkgList_to_sqlite(pkgList,'appimage.db')
		self._debug("SQL loaded")
		return(applist)
	#_process_appimage_json
	
	def _process_appimage(self,appimage,search):
		appinfo=None
		if 'links' in appimage.keys():
			if appimage['links']:
				add=True
				if search:
					if search.lower() in appimage.get('name','').lower() or search in appimage.get('description','').lower():
						pass
					else:
						add=False
				if add:
					appinfo=self.load_json_appinfo(appimage)
			  #  rebostHelper.rebostPkgList_to_sqlite([appinfo],'/tmp/.cache/rebost/xml/appimage/appimage.xml')
		return(appinfo)
		#def _th_process_appimage

	def _th_process_appimage(self,appimage,semaphore):
		semaphore.acquire()
		appinfo=None
		if appimage.get('links'):
			appinfo=self.load_json_appinfo(appimage)
		  #  rebostHelper.rebostPkgList_to_xml([appinfo],'/tmp/.cache/rebost/xml/appimage/appimage.xml')
			#rebostHelper.rebostPkg_to_sqlite(appinfo,'appimage.db')
			self.queue.put(appinfo)
		semaphore.release()
		#def _th_process_appimage

	def load_json_appinfo(self,appimage,download=False):
		appinfo=rebostHelper.rebostPkg()
		appinfo['pkgname']=appimage['name'].lower().replace("_","-").strip()
		appinfo['id']="io.appimage.{}".format(appimage['name'])
		appinfo['name']=appimage['name'].strip()
		appinfo['license']=appimage.get('license','unknown')
		description=appimage.get('description','')
		if description:
			if isinstance(description,dict):
				for lang in description.keys():
					appinfo['description']=description
					desc=".".join(description.split(".")[0:2])
					desc=" ".join(desc.split(" ")[0:8])
					desc=BeautifulSoup(desc,"html.parser").get_text()
					#desc=html.escape(desc).encode('ascii', 'xmlcharrefreplace').decode() 
			else:
				appinfo['description']=description
				desc=".".join(appinfo['description'].split(".")[0:2])
				desc=" ".join(desc.split(" ")[0:8])
				desc=BeautifulSoup(desc,"html.parser").get_text()
				#desc=html.escape(desc).encode('ascii', 'xmlcharrefreplace').decode() 
			appinfo['summary']=desc
		else:
			appinfo['summary']='Appimage of {}'.format(appinfo["name"])
			appinfo['description']='Appimage of {}'.format(appinfo["name"])
		appinfo['categories']=appimage.get('categories',"")
		icons=appimage.get('icons','')
		appinfo['icon']=appimage.get('icon','')
		if appinfo['icon'] and download:
			appinfo['icon']=self._download_file(appimage['icon'],appimage['name'],self.iconDir)
		elif icons:
			#self._debug("Loading icon %s"%appimage['icons'])
			if  download:
				#self._debug("Loading icon %s"%appimage['icons'][0])
				appinfo['icon']=self._download_file(appimage['icons'][0],appimage['name'],self.iconDir)
			else:
				appinfo['icon']=icons[0]
		appinfo['thumbnails']=appimage.get('screenshots','')
		links=appimage.get('links')
		installerurl=''
		for link in links:
			if link.get('url') and link.get('type','')=='Download' and download:
				installerUrl=self._get_releases(link['url'])
				if installerUrl.split('/')>2:
					version=installerUrl.split('/')[-2]
					appinfo['versions']['appimage']="{}".format(version)
				else:
					appinfo['versions']['appimage']="**"
			elif download==False:
				installerUrl=link['url']
			else:
				appinfo['versions']['appimage']="**"
		state="available"
		if os.path.isfile(os.path.join(self.appimageDir,"{}.appimage".format(appinfo['pkgname']))):
			state='0'
		if state==0:
			appinfo['state']['appimage']=0
		else:
			appinfo['state']['appimage']=1
		appinfo['bundle'].update({'appimage':"{}".format(installerUrl)})
		appimage['authors']=appimage.get('authors','')
		for author in appimage['authors']:
			if author.get('url',''):
				#self._debug("Author: %s"%author['url'])
				appinfo['homepage']=author['url']
		if not appimage['authors']:
			appinfo['homepage']='/'.join(appinfo['installerUrl'].split('/')[0:-1])
		return appinfo
	#def load_json_appinfo

	def fillData(self,rebostPkg):
		rebostPkg=json.loads(rebostPkg)
		bundles=rebostPkg['bundle'].get('appimage','')
		installerUrl=self._get_releases(bundles)
		if len(installerUrl.split('/'))>2:
			pkgname=installerUrl.split('/')[-1]
			pkgname=".".join(pkgname.split(".")[:-1])
			if len(pkgname.split("-"))>1:
				version=pkgname.split("-")[1]
			elif len(pkgname.split("."))>1:
				version=""
				for i in pkgname.split("."):
					if i.isnumeric():
						version+="{}.".format(i)
				version=version[:-1]
			else:
				version="0.1"
			rebostPkg['versions']['appimage']="{}".format(version)
		if installerUrl:
			rebostPkg['bundle'].update({'appimage':"{}".format(installerUrl)})
			if rebostPkg.get('icon','')=='':
				rebostPkg['icon']=self._download_file(rebostPkg['icon'],rebostPkg['name'],self.iconDir)
		else:
			rebostPkg['bundle'].pop('appimage',None)
		rebostPkg['description']=rebostHelper._sanitizeString(rebostPkg['description'])
		rebostPkg['summary']=rebostHelper._sanitizeString(rebostPkg['summary'])
		rebostPkg['name']=rebostHelper._sanitizeString(rebostPkg['name'])
		return json.dumps(rebostPkg)

	def _get_releases(self,baseUrl):
		releases=[""]
		releases_page=''
		#self._debug("Info url: %s"%app_info['installerUrl'])
		url_source=""
		try:
			if 'github' in baseUrl:
				releases_page="https://github.com"
			if 'gitlab' in baseUrl:
				releases_page="https://gitlab.com"
			if 'opensuse' in baseUrl.lower():
				releases_page=""
				url_source="opensuse"
#			   app_info['installerUrl']=app_info['installerUrl']+"/download"

			if (url_source or releases_page) and not baseUrl.lower().endswith(".appimage"):
				self._debug(baseUrl)
				content=''
				with urllib.request.urlopen(baseUrl) as f:
					try:
						content=f.read().decode('utf-8')
					except:
						self._debug("UTF-8 failed")
						pass
					soup=BeautifulSoup(content,"html.parser")
					package_a=soup.findAll('a', attrs={ "href" : re.compile(r'.*\.[aA]pp[iI]mage$')})

					for package_data in package_a:
						if url_source=="opensuse":
							package_name=package_data.findAll('a', attrs={"class" : "mirrorbrain-btn"})
						else:
							package_name=package_data.findAll('strong', attrs={ "class" : "pl-1"})
						package_link=package_data['href']
						self._debug("Link: {}".format(package_link))
						self._debug("Rel: {}".format(releases_page))
						self._debug("Source: {}".format(url_source))
						if releases_page or url_source:
							package_link=releases_page+package_link
							if baseUrl in package_link:
								releases.append(package_link)
			if releases==[]:
				releases=[baseUrl]
		except Exception as e:
			self._debug("error reading %s: %s"%(baseUrl,e))
			pass
		self._debug(releases)
		rel=''
		for release in releases:
			if release:
				rel=release
				break
		return rel
	
	def _download_file(self,url,app_name,dest_dir):
		#self._debug("Downloading to %s"%self.iconDir)
		target_file=dest_dir+'/'+app_name+".png"
		print(url)
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

