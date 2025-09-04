#!/usr/bin/python3
import os,stat
import json
import re
import hashlib
import html2text
import html
import urllib
from urllib.request import Request
from urllib.request import urlretrieve

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
		self.cache=os.path.join(self.core.CACHE,"raw")
		if not os.path.exists(self.cache):
			os.makedirs(self.cache)
		self.bundle=self.core.appstream.BundleKind.APPIMAGE
		self.repositories=["https://api.appimagehub.com/ocs/v1/content/data?format=json&language=es","https://appimage.github.io/feed.json"]
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("appimage: {}".format(msg))
	#self _debug

	def _fetchRepo(self,repo,getargs=""):
		self._debug("Fetching {}".format(repo+getargs))
		content=''
		req=Request(repo+getargs, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urllib.request.urlopen(req,timeout=3) as f:
				content=f.read().decode('utf-8')
		except Exception as e:
			print("Couldn't fetch {}".format(repo))
			self._debug(e)
		return(content)
	#def _fetchRepo

	def _chkUpdateNeeded(self,repo,content):
		update=True
		frepo=os.path.join(self.cache,"{}".format(repo.split("/")[2]))
		data=content.copy()
		if "data" in data.keys():
			data["data"]=""
		ccontent=json.dumps(data,separators=(',',':'))
		chash=hashlib.md5(ccontent.encode("utf-8")).hexdigest()
		if os.path.exists(frepo):
			with open(frepo,"r") as f:
				fhash=f.read().strip()
			if chash==fhash:
				update=False
		with open(frepo,"w") as f:
			f.write(chash)
		return(update)
	#def _chkUpdateNeeded

	def _getAppstreamFromDataField(self,jdata):
		self._debug("Processing data for {} apps".format(len(jdata)))
		apps=[]
		htmlparser=html2text.HTML2Text()
		htmlparser.scape_snob=True
		htmlparser.unicode_snob=True
		for japp in jdata:
			if not japp.get("downloadname1","").lower().endswith("appimage"):
				continue
			if japp.get("download_package_type1","").lower()=="appimage":
				name=japp['name'].replace(' - AppImage',"").replace(' - Appimage',"").replace("/","_").replace("\\","_").replace("\"","").replace("\'","")
				if name=="":
					continue
				app=self.core.appstream.App()
				desc=html.escape(htmlparser.handle(japp["description"]).replace("\n","").strip()).replace(":"," - ")
				if len(desc)==0:
					desc="Download 'n' run"
				summary=html.escape(htmlparser.handle(japp["summary"]).replace("\n","").strip())
				summary=htmlparser.handle(japp['summary']).replace("\n","").strip()
				if len(summary)==0:
					summary="Appimage"
				app.set_name("C",name)
				app.set_description("C",desc)
				app.set_comment("C",summary)
				for tag in japp.get("tags","").split(","):
					app.add_keyword("C",tag)
				app.set_developer_name("C",japp.get("personid",""))
				app.add_category(japp.get("typename",""))
				app.add_pkgname(".".join(japp.get("downloadname1","").split(".")[0:-1]))
				app.add_url(self.core.appstream.UrlKind.HOMEPAGE,japp.get("detailpage",""))
				icn=japp.get("previewpic1","")
				appicon=self.core.appstream.Icon()
				appicon.set_kind(self.core.appstream.IconKind.REMOTE)
				appicon.set_name(os.path.basename(icn))
				appicon.set_url(icn)
				app.add_icon(appicon)
				screenshots=self.core.appstream.Screenshot()
				for imgfield in ["previewpic2","smallpreviewpic1","smallpreviewpic2"]:
					appimg=self.core.appstream.Image()
					if "small" in imgfield:
						appimg.set_kind(self.core.appstream.ImageKind.THUMBNAIL)
					else:
						appimg.set_kind(self.core.appstream.ImageKind.SOURCE)
					img=japp.get(imgfield,"")
					if len(img)>0:
						appimg.set_url(img)
						screenshots.add_image(appimg)
				app.add_screenshot(screenshots)
				bun=self.core.appstream.Bundle()
				bun.set_kind(self.core.appstream.BundleKind.APPIMAGE)
				bun.set_id(japp.get("downloadlink1",""))
				app.add_bundle(bun)
				apprelease=self.core.appstream.Release()
				release=japp.get("download_version1","unknown")
				apprelease.set_size(self.core.appstream.SizeKind.DOWNLOAD,japp.get("downloadsize1",""))
				apprelease.set_version(release)
				app.add_release(apprelease)
				idname=app.get_name("C")
				if idname.lower().endswith(".appimage"):
					idname=".".join(idname.strip().split(".")[0:-1])
				app.set_id("com.appimagehub.{}".format(idname.replace(" ","")))
				#self._debug("Added {} - {}".format(name,app.get_pkgname_default()))
				status="available"
				app.add_metadata("X-REBOST-appimage","{};{}".format(release,status))
				if status=="installed":
					app.set_state(self.core.appstream.AppState.INSTALLED)
				apps.append(app)
		return(apps)
	#def _getAppstreamFromDataField

	def _getAppstreamFromItemsField(self,jdata):
		self._debug("Processing items for {} apps".format(len(jdata)))
		apps=[]
		htmlparser=html2text.HTML2Text()
		htmlparser.scape_snob=True
		htmlparser.unicode_snob=True
		for japp in jdata:
			name=japp.get("name","").replace(" - AppImage","").replace(" - Appimage","")
			if name=="":
				continue
			app=self.core.appstream.App()
			desc=self.core.appstream.markup_import(japp.get("description","").strip(),self.core.appstream.MarkupConvertFormat.SIMPLE)
			if desc==None:
				desc="Download 'n' run"
			elif len(desc)==0:
				desc="Download 'n' run"
			summary=self.core.appstream.markup_import(japp.get("summary",""),self.core.appstream.MarkupConvertFormat.SIMPLE).strip().replace("<p>","",).replace("</p>","")
			if len(summary)==0:
				summary="Appimage"
			author=japp.get("authors",[{}])
			app.set_name("C",name)
			app.set_comment("C",summary)
			app.set_description("C",desc)
			if isinstance(author,dict):
				app.set_developer_name("C",author.get("name",""))
			for cat in japp.get("categories",[]):
				if cat!=None:
					app.add_category(cat)
			icn=japp.get("icon","")
			if len(icn)==0:
				icons=japp.get('icons',[])
				if isinstance(icons,list):
					icn=icons[0]
			if len(icn)>0 and not icn.startswith("http"):
				icn="https://appimage.github.io/database/{}".format(icn)
			appicon=self.core.appstream.Icon()
			appicon.set_kind(self.core.appstream.IconKind.REMOTE)
			appicon.set_name(os.path.basename(icn))
			appicon.set_url(icn)
			if len(icn.strip())>0:
				app.add_icon(appicon)
			screenshots=self.core.appstream.Screenshot()
			scrs=japp.get("screenshots",[])
			if isinstance(scrs,list):
				for f in scrs:
					appimg=self.core.appstream.Image()
					urlimg="https://appimage.github.io/database/{}".format(f)
					if "small" in f:
						appimg.set_kind(self.core.appstream.ImageKind.THUMBNAIL)
					else:
						appimg.set_kind(self.core.appstream.ImageKind.SOURCE)
					appimg.set_url(urlimg)
					screenshots.add_image(appimg)
			app.add_screenshot(screenshots)
		#REM FIX RELEASES
		#	apprelease=self.core.appstream.Release()
		#	apprelease.set_size(self.core.appstream.SizeKind.DOWNLOAD,japp.get("downloadsize1",""))
		#	apprelease.set_version(japp.get("download_version1"))
		#	app.add_release(apprelease)
		#	app.set_id("com.appimagehub.{}".format(app.get_pkgname_default()))
			links=japp.get('links')
			installerurl=''
			release="unknown"
			status="available"
			while links:
				link=links.pop(0)
				if link.get('url') and link.get('type','').lower()=='download':
					installerUrl=link['url']
		#REM FIX RELEASES
					if installerUrl.split('/')>2:
						release=installerUrl.split('/')[-2]
			bun=self.core.appstream.Bundle()
			bun.set_kind(self.core.appstream.BundleKind.APPIMAGE)
			bun.set_id(installerUrl)
			app.add_bundle(bun)
			app.set_id("io.github.{}".format(name.lower().replace(" ","")))
			app.add_metadata("X-REBOST-appimage","{};{}".format(release,status))
			apps.append(app)
		return(apps)
	#def _getAppstreamFromItemsField

	def getAppstreamData(self):
		store=self.core.appstream.Store()
		store.set_origin("appimage")
		for repo in self.repositories:
			fxml=os.path.join(self.cache,"{}.xml".format(repo.split("/")[2]))
			try:
				repo_raw=self._fetchRepo(repo)
				jrepo=json.loads(repo_raw)
			except Exception as e:
				print("Error in {}: {}".format(repo,e))
				store=self.core._fromFile(store,fxml)
			else:
				if self._chkUpdateNeeded(repo,jrepo)==False:
					self._debug("Loading from cache")
					store=self.core._fromFile(store,fxml)
				if len(store.get_apps())==0:
					if "data" in jrepo.keys(): #json responde with data field for the pkgs
						itemsperpage=jrepo.get("itemsperpage",0)
						totalitems=jrepo.get("totalitems",0)
						data=jrepo["data"]
						page=0
						if totalitems>itemsperpage:
							while len(jrepo.get("data",[]))>0:
								page+=1
								repo_raw=self._fetchRepo(repo,getargs="&pagesize=100&page={}".format(page))
								jrepo=json.loads(repo_raw)
								data.extend(jrepo.get("data",[]))
								
						store.add_apps(self._getAppstreamFromDataField(data))
					elif "items" in jrepo.keys(): #json responde with items field for the pkgs
						store.add_apps(self._getAppstreamFromItemsField(jrepo["items"]))
					self.core._toFile(store,fxml)
		self._debug("Sending {}".format(len(store.get_apps())))
		return(store)
	#def getAppstreamData
