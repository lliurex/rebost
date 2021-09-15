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


class appimageHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(asctime)s %(message)s')
		self.enabled=True
		self.packagekind="appimage"
		self.actions=["search","load","install","remove"]
		#self.autostartActions=["load"]
		self.priority=1
		self.store=None
		self.progressQ={}
		self.progress={}
		self.resultQ={}
		self.result={}
		self.appimageDir=os.getenv("HOME")+"/Applications"
		self.wrkDir=os.path.join(os.getenv("HOME"),".cache/rebost/xml/appimage")
		self.wrkDir="/tmp/.cache/rebost/xml/appimage"
		self.iconDir="/tmp/.cache/rebost/icons"
		self.metadataLoc=['/usr/share/metainfo',self.wrkDir]
		self.repos={'appimagehub':{'type':'json','url':'https://appimage.github.io/feed.json','url_info':''}}
		self.store=''
		self._loadStore()
		#self.store=appstream.Pool()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("appimage: %s"%str(msg))
	
	def execute(self,action,*args):
		rs=''
		if action=='search':
			rs=self._searchPackage(*args)
		return(rs)

	def _searchPackage(self,package):
		searchResults=[]
		searchResults=self._process_appimage_json(self.store,package)
		return(searchResults)

	def execute2(self,procId,action,progress,result,store,args=''):
		self.procId=procId
		if action in self.actions:
			self.progressQ[action]=progress
			self.resultQ[action]=result
			self.progress[action]=0
			if action=='load':
				self._loadStore()
			if action=='install':
				self._install(args)
			if action=='remove':
				self._remove(args)

	def _callback(self,partial_size=0,total_size=0):
		action='install'
		limit=99
		if partial_size!=0 and total_size!=0:
			inc=round(partial_size/total_size,2)*100
			self.progress[action]=inc
		else:
			inc=1
			margin=limit-self.progress[action]
			inc=round(margin/limit,3)
			self.progress[action]=(self.progress[action]+inc)
		if (self.progress[action]>limit):
			self.progress[action]=limit
		self.progressQ[action].put(int(self.progress[action]))
	#def _callback

	def _install(self,pkg):
		#app_info=self._get_info(app_info,force=True)
		action='install'
		self._debug("Installing %s"%pkg)
		result=rebostHelper.resultSet()
		result['id']=self.procId
		result['name']=action
		result['description']='%s'%pkg['pkgname']
		appimageUrl=pkg['bundle'].get('appimage','')
		if not appimageUrl:
			self._debug("No url")
			self.progressQ[action].put(100)
			result['error']=1
			result['errormsg']="Link not available"
			self.resultQ[action].put(str(json.dumps([result])))
		else:
			self._debug("Downloading "+appimageUrl)
			dest_path=self.appimageDir+'/'+"%s.appimage"%pkg.get('pkgname')
			try:
				req=Request(appimageUrl, headers={'User-Agent':'Mozilla/5.0'})
				with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
					bf=16*1024
					acumbf=0
					app_size=int(response.info()['Content-Length'])
					while True:
						if acumbf>=app_size:
							break
						shutil.copyfileobj(response, out_file,bf)
						acumbf=acumbf+bf
						self._callback(acumbf,app_size)
				st = os.stat(dest_path)
				os.chmod(dest_path, st.st_mode | 0o755)
				result['error']=0
				result['errormsg']=""
			except Exception as e:
				result['error']=2
				result['errormsg']=str(e)
				self._debug(e)
			self.resultQ[action].put(str(json.dumps([result])))
			self.progressQ[action].put(100)
		#return app_info
	#def _install_appimage

	def _remove(self,pkg):
		#self._debug("Removing "+app_info['package'])
		action='remove'
		result=rebostHelper.resultSet()
		result['id']=self.procId
		result['name']=action
		result['description']='%s'%pkg['pkgname']
		f_name=os.path.join(self.appimageDir+'/',"%s.appimage"%pkg['pkgname'])
		if os.path.isfile(f_name):
			try:
				subprocess.run([f_name, "--remove-appimage-desktop-integration"])
				result['error']=0
				result['errormsg']=""
			except Exception as e:
				result['error']=3
				result['errormsg']=str(e)
			try:
				os.remove(f_name)
			except Exception as e:
				result['error']=4
				result['errormsg']=str(e)
		else:
			result['error']=5
			result['errormsg']="File %s not found"%f_name
		self.resultQ[action].put(str(json.dumps([result])))
		self.progressQ[action].put(100)
	#def _remove_appimage

	def _loadStore(self):
		action="load"
		result=rebostHelper.resultSet()
		#result['id']=self.procId
		result['name']=action
		(result['error'],result['msg'])=self._get_bundles_catalogue()
#	   self.progressQ[action].put(100)
#	   self.resultQ[action].put(str(json.dumps([result])))
	
	def _chk_update(self):
		return False

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
				#self.store=appimageJson
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
				time.sleep(0.5)
			for th in thlist:
				th.join()
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
		if 'links' in appimage.keys():
			if appimage['links']:
				appinfo=self.load_json_appinfo(appimage)
			  #  rebostHelper.rebostPkgList_to_xml([appinfo],'/tmp/.cache/rebost/xml/appimage/appimage.xml')
				rebostHelper.rebostPkgList_to_sqlite(appinfo,'appimage.sql')
		semaphore.release()
		#def _th_process_appimage

	def load_json_appinfo(self,appimage):
		#self._debug(appimage)
		#appinfo=self._init_appinfo()
		appinfo=rebostHelper.rebostPkg()
		appinfo['pkgname']=appimage['name'].lower().replace("_","-")
		appinfo['id']="io.appimage.{}".format(appimage['name'])
		appinfo['name']=appimage['name']
		if 'license' in appimage.keys():
			appinfo['license']=appimage['license']
		if 'description' in appimage.keys():
			if isinstance(appimage['description'],dict):
				for lang in appinfo['description'].keys():
					appinfo['description'].update({lang:appimage['description'][lang]})
					desc=".".join(appinfo['description'][lang].split(".")[0:2])
					desc=" ".join(desc.split(" ")[0:8])
					appinfo['summary'].update({lang:desc})
			else:
				appinfo['description']={"C":appimage['description']}
				desc=".".join(appinfo['description']["C"].split(".")[0:2])
				desc=" ".join(desc.split(" ")[0:8])
				appinfo['summary'].update({"C":desc})
		else:
			appinfo['summary']={"C":'Appimage of {}'.format(appinfo["name"])}
		if 'categories' in appimage.keys():
			appinfo['categories']=appimage['categories']
		if 'icon' in appimage.keys():
			appinfo['icon']=self._download_file(appimage['icon'],appimage['name'],self.iconDir)
		elif 'icons' in appimage.keys():
			self._debug("Loading icon %s"%appimage['icons'])
			if appimage['icons']:
				self._debug("Loading icon %s"%appimage['icons'][0])
				appinfo['icon']=self._download_file(appimage['icons'][0],appimage['name'],self.iconDir)
		if 'screenshots' in appimage.keys():
			appinfo['thumbnails']=appimage['screenshots']
		if 'links' in appimage.keys():
			if appimage['links']:
				for link in appimage['links']:
					if 'url' in link.keys() and link['type']=='Download':
						appinfo['installerUrl']=self._get_releases(link['url'])
						if len(appinfo['installerUrl'].split('/'))>2:
							version=appinfo['installerUrl'].split('/')[-2]
							appinfo['version']="appimage-{}".format(version)
						else:
							appinfo['version']="appimage-**"
						state="available"
						if os.path.isfile(os.path.join(self.appimageDir,"{}.appimage".format(appinfo['pkgname']))):
							state='installed'
						appinfo['bundle'].update({'appimage':"{};amd64;{}".format(appinfo['installerUrl'],state)})
		if 'authors' in appimage.keys():
			if appimage['authors']:
				for author in appimage['authors']:
					if 'url' in author.keys():
						#self._debug("Author: %s"%author['url'])
						appinfo['homepage']=author['url']
		else:
			appinfo['homepage']='/'.join(appinfo['installerUrl'].split('/')[0:-1])
		return appinfo
	#def load_json_appinfo

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
				content=''
				with urllib.request.urlopen(baseUrl) as f:
					try:
						content=f.read().decode('utf-8')
					except:
						#self._debug("UTF-8 failed")
						pass
					soup=BeautifulSoup(content,"html.parser")
					package_a=soup.findAll('a', attrs={ "href" : re.compile(r'.*\.[aA]pp[iI]mage$')})

					for package_data in package_a:
						if url_source=="opensuse":
							package_name=package_data.findAll('a', attrs={"class" : "mirrorbrain-btn"})
						else:
							package_name=package_data.findAll('strong', attrs={ "class" : "pl-1"})
						package_link=package_data['href']
						if releases_page or url_source:
							package_link=releases_page+package_link
							if baseUrl in package_link:
								releases.append(package_link)
								self._debug("Link: {}".format(package_link))
			if releases==[]:
				releases=[baseUrl]
		except Exception as e:
			self._debug("error reading %s: %s"%(baseUrl,e))
			pass
		#self._debug(releases)
		rel=''
		for release in releases:
			if release:
				rel=release
				break
		return rel
	
	def _download_file(self,url,app_name,dest_dir):
		self._debug("Downloading to %s"%self.iconDir)
		target_file=dest_dir+'/'+app_name+".png"
		if not url.startswith('http'):
			url="https://appimage.github.io/database/%s"%url
#	   if not os.path.isdir(self.iconDir):
#		   os.makedirs(self.iconDir)
#	   if not os.path.isfile(target_file):
#		   self._debug("Downloading %s to %s"%(url,target_file))
#		   try:
#			   with urllib.request.urlopen(url) as response, open(target_file, 'wb') as out_file:
#				   bf=16*1024
#				   acumbf=0
#				   file_size=int(response.info()['Content-Length'])
#				   while True:
#					   if acumbf>=file_size:
#						   break
#					   shutil.copyfileobj(response, out_file,bf)
#					   acumbf=acumbf+bf
#			   st = os.stat(target_file)
#		   except Exception as e:
#			   self._debug("Unable to download %s"%url)
#			   self._debug("Reason: %s"%e)
#			   target_file=''
#	   else:
#		   self._debug("{} already downloaded".format(self.iconDir))
		return(target_file)
	#def _download_file

def main():
	obj=appimageHelper()
	return (obj)


a=appimageHelper()
