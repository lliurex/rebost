#!/usr/bin/python3
import os,ssl
import json
import html2text
import html
from urllib.request import Request,urlopen
import gi
gi.require_version('AppStream', '1.0')
from gi.repository import AppStream as appstream

class fetcher:
	def __init__(self,*args,**kwargs):
		self.name="appimage"
		self.dbg=True
		self.bundle=appstream.BundleKind.APPIMAGE
		self.mapping={}
		self.cache=os.path.join("/tmp","appstream","cache",self.name)
		if os.path.exists(self.cache)==False:
			os.makedirs(self.cache)
		self.priority=10
		self.repositories=["https://api.appimagehub.com/ocs/v1/content/data?format=json&language=es","https://appimage.github.io/feed.json"]
		self.headers={"User-Agent": "LliurexFetcher/1.0 (https://lliurex.net)","Accept": "application/vnd.github.v3+json"}
		self.store=kwargs["store"]
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("{0}: {1}".format(self.name,msg))
	#self _debug

	def _fetchRepo(self,repo,getargs=""):
		self._debug("Fetching {}".format(repo+getargs))
		cache=os.path.basename(repo.removesuffix("/").split("?")[0])
		cache=os.path.join(self.cache,cache)
		self._debug("Cache: {}".format(cache))
		content=''
		if os.path.exists(cache):
			with open(cache,"r") as f:
				content=f.read()
		else:
			req=Request(repo+getargs, headers=self.headers)
			context=ssl.create_default_context()
			context.check_hostname=False
			context.verify_mode=ssl.CERT_NONE
			try:
				with urlopen(req,timeout=3,context=context) as f:
					content=f.read().decode('utf-8')
			except Exception as e:
				print("Couldn't fetch {}".format(repo))
				#self._debug(e)
			else:
				with open(cache,"w") as f:
					f.write(content)
		return(content)
	#def _fetchRepo

	def _setLaunchable(self,app,japp):
		launchable=appstream.Launchable()
		launchable.set_kind(appstream.LaunchableKind.UNKNOWN)
		app.add_launchable(launchable)
	#def _setLaunchable

	def _setDescription(self,app,japp):
		htmlparser=html2text.HTML2Text()
		htmlparser.scape_snob=True
		htmlparser.unicode_snob=True
		desc=japp.get("description","").strip()
		if desc==None:
			desc="Appimage"
		elif len(desc)==0:
			desc="Appimage"
		desc=html.escape(htmlparser.handle(desc).replace("\n","").strip()).replace(":"," - ").replace("&","and")
		desc="<p>{}</p>".format(desc)
		app.set_description(desc,"C")
		summary=japp.get("summary","")
		if isinstance(summary,str)==False:
			descArray=desc.split(" ")
			summary=" ".join(descArray[0:min(20,len(descArray))])
		summary=summary.strip().replace("<p>","",).replace("</p>","")
		summary=html.escape(htmlparser.handle(summary).replace("\n","").strip()).replace(":"," - ").replace("&","and")
		if len(summary)==0:
			summary="Appimage"
		app.set_summary(summary,"C")
	#def _setDescription

	def _setAuthor(self,app,japp):
		author=japp.get("authors",japp.get("personid"))
		if author!=None:
			devel=appstream.Developer()
			if isinstance(author,list):
				authorId=str(author[0].get("name","anonymous"))
			else:
				authorId=str(author)
			devel.set_id(authorId)
			devel.set_name(authorId)
			app.set_developer(devel)
	#def _setAuthor

	def _addCategories(self,app,japp):
		if "typename" in japp.keys():
			japp["categories"]=[japp["typename"]]
		for cat in japp.get("categories",[]):
			if cat!=None:
				app.add_category(cat)
	#def _addCategories

	def _setIcon(self,app,japp):
		if "icons" in japp.keys():
			icons=japp.get('icons',[])
			if isinstance(icons,list):
				icn=icons[0]
			else:
				icn=""
		else:
			icn=japp.get("icon",japp.get("smallpreviewpic1"))
		if len(icn)>0 and not icn.startswith("http"):
			icn="https://appimage.github.io/database/{}".format(icn)
		if len(icn.strip())>0:
			appicon=appstream.Icon()
			appicon.set_kind(appstream.IconKind.REMOTE)
			appicon.set_name(os.path.basename(icn))
			appicon.set_url(icn)
			app.add_icon(appicon)
	#def _setIcon

	def _addScreenshots(self,app,japp):
		if "screenshots" in japp.keys():
			scrs=japp.get("screenshots",[])
		else:
			if "previewpic1" in japp.keys():
				idx=1
				scrs=[]
				scr=japp.get("previewpic{}".format(idx))
				while scr!=None:
					scr=japp.get("previewpic{}".format(idx))
					scrs.append(scr)
					idx+=1
		if isinstance(scrs,list):
			if len(scrs)>0:
				screenshots=appstream.Screenshot()
				for f in scrs:
					if f==None:
						continue
					appimg=appstream.Image()
					if f.startswith("http")==False:
						urlimg="https://appimage.github.io/database/{}".format(f)
					else:
						urlimg=f
					if "small" in f:
						appimg.set_kind(appstream.ImageKind.THUMBNAIL)
					else:
						appimg.set_kind(appstream.ImageKind.SOURCE)
					appimg.set_url(urlimg)
					screenshots.add_image(appimg)
				app.add_screenshot(screenshots)
	#def _addScreenshots

	def _getJsonLastRelease(self,japp):
		release={"latest":""}
		if "download_package_arch1" in japp.keys():
			idx=1
			arch=japp.get("download_package_arch{}".format(idx))
			while arch!=None:
				if arch=="" or "x86" in arch.lower():
					tag=japp.get("download_version{}".format(idx),"latest")
					candidateUrl=japp.get("downloadlink{}".format(idx))
					if candidateUrl.lower().endswith(".appimage"):
						release={tag:candidateUrl}
						break
				idx+=1
				arch=japp.get("download_package_arch{}".format(idx))
		return(release)
	#def _getJsonLastRelease

	def _getGithubExtendedData(self,apiUrl):
		release={"latest":apiUrl}
		req=Request(apiUrl, headers=self.headers)
		try:
			with urlopen(req,timeout=2) as f:
				contents=json.loads(f.read().decode('utf-8'))
		except Exception as e:
			self._debug("Couldn't fetch {}".format(gitUrl))
			self._debug(e)
		else:
			if len(contents)>0:
				for content in contents:
					appimages=[]
					tag=content.get("tag_name",content.get("tag"))
					assets=content.get("assets")
					for asset in assets:
						if asset.get("name","").lower().endswith(".appimage"):
							candidateUrl = asset["browser_download_url"]
							appimages.append(candidateUrl)
							if "x86" in candidateUrl:
								appimages=[candidateUrl]
								break
					if len(appimages)>0:
						release={tag:appimages[0]}
		return(release)
	#def _getGithubExtendedData

	def _getGithubLastRelease(self,japp,extendedInfo=False):
		releaseLinks=japp["links"]
		gitUrl=""
		release={"latest":gitUrl}
		if releaseLinks!=None:
			if len(releaseLinks)>1:
				if isinstance(releaseLinks[1],dict):
					if releaseLinks[1]["type"].lower()=="download":
						gitUrl=releaseLinks[1]["url"]
		if len(gitUrl)>0:
			headers = {"Accept": "application/vnd.github.v3+json"}
			splitUrl=gitUrl.split("/")
			apiUrl="https://api.github.com/repos/{0}/{1}/releases".format(splitUrl[3],splitUrl[4])
			release={"latest":apiUrl}
			if extendedInfo==True: #github rate limit is too low for this, only for selected apps
				release=self._getGithubExtendedData(apiUrl)
		return(release)
	#def _getGithubLastRelease

	def _setRelease(self,app,japp,extendedInfo=False):
		release={"latest":""}
		if "version" in japp.keys():
			release=self._getJsonLastRelease(japp)
		elif "links" in japp.keys():
			release=self._getGithubLastRelease(japp,extendedInfo)
		appRelease=appstream.Release()
		appRelease.set_kind(appstream.ReleaseKind.STABLE)
		for version,url in release.items():
			appRelease.set_version(version)
			artifact=appstream.Artifact()
			artifact.set_kind(appstream.ArtifactKind.BINARY)
			artifact.set_bundle_kind(appstream.BundleKind.APPIMAGE)
			artifact.add_location(url)
			artifact.set_filename(os.path.basename(url.removesuffix("/")))
			appRelease.add_artifact(artifact)
		app.add_release(appRelease)
	#def _setRelease
				
	def _getAppstreamFromJson(self,jdata):
		self._debug("Processing json for {} apps".format(len(jdata)))
		apps=appstream.ComponentBox()
		apps=[]
		for japp in jdata:
			extendedInfo=False
			name=japp.get("name","").replace(" - AppImage","").replace(" - Appimage","")
			if name=="":
				continue
			cid=name.split(" ")[0].lower()
			if cid in self.mapping["aliases"]:
				self._debug("Map {0}->{1}".format(cid,self.mapping["aliases"][cid]))
				#cid="hub.appimage.{}".format(self.mapping["aliases"][cid])
				cid=self.mapping["aliases"][cid]
				extendedInfo=True
			if cid in self.mapping["nodisplay"]:
				cid=""
			if cid!="":
				app=appstream.Component()
				app.set_priority(self.priority)
				app.set_id("{}".format(cid))
				app.set_kind(appstream.ComponentKind.DESKTOP_APP)
				app.set_merge_kind(appstream.MergeKind.APPEND)
				if cid in self.cids and "ocrfeeder" in cid:
					app.set_merge_kind(appstream.MergeKind.REPLACE|appstream.MergeKind.REPLACE)
				self.cids.append(cid)
				app.set_name(name,"C")
				self._setLaunchable(app,japp)
				self._setDescription(app,japp)
				self._setAuthor(app,japp)
				self._addCategories(app,japp)
				self._setIcon(app,japp)
				self._addScreenshots(app,japp)
				self._setRelease(app,japp,extendedInfo)
				apps.append(app)
		return(apps)
	#def _getAppstreamFromItemsField

	def fetchCatalogue(self,mapping={}):
		store=appstream.Metadata()
		store.set_origin("appimage")
		store.set_update_existing(False)
		store.set_format_version(appstream.FormatVersion.V1_0)
		self.mapping["nodisplay"]=mapping.get("nodisplay",[])
		self.mapping["aliases"]=mapping.get("aliases",{})
		self.cids=[]
		for repo in self.repositories:
			try:
				repoRaw=self._fetchRepo(repo)
				jrepo=json.loads(repoRaw)
			except Exception as e:
				#print("Error in {}: {}".format(repo,e))
				pass
			else:
				if "data" in jrepo.keys(): #json responde with data field for the pkgs
					itemsperpage=jrepo.get("itemsperpage",0)
					totalitems=jrepo.get("totalitems",0)
					data=jrepo["data"]
					page=0
					if totalitems>itemsperpage:
						while len(jrepo.get("data",[]))>0:
							page+=1
							repoRaw=self._fetchRepo(repo,getargs="&pagesize=100&page={}".format(page))
							if repoRaw!=None:
								try:
									jrepo=json.loads(repoRaw)
									data.extend(jrepo.get("data",[]))
								except Exception as e:
									self._debug("Failed to parse {}".format(repo))
									self._debug(e)
									self._debug("--------/>")
									break

				elif "items" in jrepo.keys(): #json responde with items field for the pkgs
					data=jrepo["items"]
				apps=self._getAppstreamFromJson(data)
				for app in apps:
					store.add_component(app)
					self.store.add_component(app)
		return(store)
	#def fetchCatalogue
#class engine
