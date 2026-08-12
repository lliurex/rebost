#!/usr/bin/env python3
import os
import html2text
import gi
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream
import json
import html
import tempfile
import subprocess
import locale

def _getLocale():
	langs=[]
	for localLang in locale.getlocale():
		if "_" in localLang:
			langs.append(localLang.split("_")[0])
			langs.append(localLang.split("_")[-1].lower())
	if "ca" in langs:
		idx=langs.index("ca")
		if "qcv" not in langs:
			langs.insert(idx,"qcv")
		if "ca-valencia" not in langs:
			langs.insert(idx,"ca-valencia")
	langs.append("C")
	return(langs)
#def _getLocale

def _sanitizeString(data,scape=False,unescape=False):
	if isinstance(data,str):
		data=html2text.html2text(data)#,"lxml")
		data=data.replace("&","and")
		data=data.replace("`","")
		data=data.replace("´","")
		data=data.replace("\n"," ")
		data=data.replace("\\","*")
		data=data.rstrip()
		if scape:
			data=html.escape(data).encode('ascii', 'xmlcharrefreplace').decode() 
			data=data.replace("<","")
			data=data.replace(">","")
		if unescape:
			data=html.unescape(data)
	return(data)
#def _sanitizeString

def getFreedesktopCategories():
	#From freedesktop https://specifications.freedesktop.org/menu-spec/latest/category-registry.html
	catTree={"AudioVideo":["DiscBurning"],
		"Audio":["Midi","Mixer","Sequencer","Tuner","Recorder","Player"],
		"Video":["AudioVideoEditing","Player","Recorder","TV"],
		"Development":["Building","Debugger","IDE","GUIDesigner","Profiling","RevisionControl","Translation","Database","ProjectManagement","WebDevelopment"],
		"Education":["Art","Construction","Music","Languages","ArtificialIntelligence","Astronomy","Biology","Chemistry","ComputerScience","DataVisualization","Economy","Electricity","Geography","Geology","Geoscience","History","Humanities","ImageProcessing","Literature","Maps","Math","NumericalAnalysis","MedicalSoftware","Physics","Robotics","Spirituality","Sports","ParallelComputing"],
		"Game":["ActionGame","AdventureGame","ArcadeGame","BoardGame","BlocksGame","CardGame","Emulator","KidsGame","LogicGame","RolePlaying","Shooter","Simulation","SportsGame","StrategyGame","LauncherStore"],
		"Graphics":["2DGraphics","VectorGraphics","RasterGraphics","3DGraphics","Scanning","OCR","Photography","Publishing","Viewer"],
		"Network":["Email","Dialup","InstantMessaging","Chat","IRCCLient","Feed","FileTransfer","HamRadio","News","P2P","RemoteAcces","Telephony","TelephonyTools","VideoConference","WebBrowser","WebDevelopment"],
		"Office":["Calendar","ContactManagement","Database","Dictionary","Chart","Email","Finance","FlowChart","PDA","ProjectManagement","Presentation","Spreadsheet","WordProcessor","Photography","Publishing","Viewer"],
		"Science":["Construction","Languages","ArtificialIntelligence","Astronomy","Biology","Chemistry","ComputerScience","DataVisualization","Economy","Electricity","Geography","Geology","Geoscience","History","Humanities","Literature","Math","NumericalAnalysis","MedicalSoftware","Physics","Robotics","ParallelComputing"],
		"Settings":["Security","Accessibility"],
		"System":["Security","Emulator","FileTools","FileManager","TerminalEmulator","FileSystem","Monitor"],
		"Utility":["TextTools","TelephonyTools","Maps","Archiving","Compression","FileTools","Accessibility","Calculator","Clock","TextEditor"]
		}
	return(catTree)
#def getCategories

def _getIconFromAppstream(app):
	iconf=""
	for icon in app.get_icons():
		if icon.get_filename():
			iconf=icon.get_filename()
			break
		url=icon.get_url()
		if url:
			if url.startswith("http"):
				iconf=url
				break
	return(iconf)
#def _getIconFromAppstream

def _setDetailFromAppstream(app,pkg):
	versionArray=[]
	for release in app.get_releases():
		versionArray.append(release.get_version())
	if len(app.get_bundles())>0:
		for bundle in app.get_bundles():
			bundleKind=bundle.kind_to_string(bundle.get_kind())
			if bundleKind==None:
				bundleKind="unknown"
			pkg["bundle"].update({bundleKind:bundle.get_id()})
			pkg['versions']={}
			metadata=app.get_metadata()
			if metadata!=None:
				for key,data in metadata.items():
					if key.startswith("X-REBOST-"):
						mkey=key.replace("X-REBOST-","")
						if mkey=="hidden":
							pkg["hidden"]=True
						else:
							if ";" in data:
								(release,status)=data.split(";")
								if status=="installed":
									pkg["status"].update({mkey:0})
								else:
									pkg["status"].update({mkey:1})
								pkg["versions"].update({mkey:release.split(" ")[0]})
			if len(pkg["versions"])==0 and len(versionArray)>0:
				pkg["versions"].update({"package":versionArray[0]})
	pkg["state"]=app.get_state()
	pkg["suggests"]=[]
	for suggest in app.get_suggests():
		pkg["suggests"].extend(suggest.get_ids())
	pkg["suggests"]=list(set(pkg["suggests"]))
	pkg["keywords"]=[]
	if app.get_origin()=="verified":
		kudos=app.get_kudos()
		if "ASSISTED" in kudos:
			pkg["assisted"]=True
		if "BLOCKED" in kudos:
			pkg["forbidden"]=True
		if "WEBAPP" in kudos:
			pkg["webapp"]=True
		if "UNAVAILABLE" in kudos:
			pkg["unavailable"]=True
	pkg["origin"]=app.get_origin()
	localLangs=_getLocale()
	for lang in localLangs:
		pkg["keywords"].extend(app.get_keywords(lang))
		if len(pkg["keywords"])>0:
			break
	return(pkg)
#def _setDetailFromAppstream

def _getScreenshotsFromAppstream(app):
	screenshots=[]
	for scr in app.get_screenshots():
		for img in scr.get_images():
			screenshots.append(img.get_url())
			break
		if len(screenshots)>3:
			break
	return(screenshots)
#def _getScreenshotsFromAppstream

def _appstreamAppToRebost(app):
	pkg={"bundle":{},"versions":{},"status":{}}
	pkg['id']=app.get_id().lower()
	tmpSummary=None
	tmpDescription=None
	tmpName=None
	localLangs=_getLocale()
	if len(localLangs)>0:
		if localLangs[0].startswith("ca") and localLangs[0]!="ca":
			localLangs.insert(0,"ca")
	
	for lang in localLangs:
		if tmpName==None:
			tmpName=app.get_name(lang)
		if tmpSummary==None:
			if isinstance(app.get_comment(lang),str)==True:
				if app.get_comment(lang)!="":
					tmpSummary=app.get_comment(lang)
		if tmpDescription==None:
			if isinstance(app.get_description(lang),str)==True:
				tmpDescription=app.get_description(lang)
		if tmpSummary!=None and tmpDescription!=None and tmpName!=None:
			if tmpSummary!="" and tmpDescription!="" and tmpName!="":
				break
	if tmpSummary==None:
		tmpSummary=app.get_comment("C")
	if tmpDescription==None:
		tmpDescription=app.get_description("C")
	if tmpName==None:
		tmpName=pkg["id"]
	if isinstance(tmpDescription,str)==False:
		tmpDescription=tmpSummary
	pkg["name"]=tmpName
	pkg["description"]=tmpDescription
	pkg["summary"]=tmpSummary
	if app.get_pkgname_default()!=None:
		pkg['pkgname']=app.get_pkgname_default()
	else:
		pkg['pkgname']=pkg['name']
	pkg['pkgname']=pkg['pkgname'].strip().replace("-desktop","")
	pkg['icon']=_getIconFromAppstream(app)
	pkg['homepage']=app.get_url_item(appstream.UrlKind.HOMEPAGE)
	for url in [appstream.UrlKind.CONTACT,appstream.UrlKind.DETAILS,appstream.UrlKind.HELP]:
		pkg['infopage']=app.get_url_item(url)
		if pkg["infopage"]!=None:
			if len(pkg["infopage"])>0:
				break
		else:
			pkg["infopage"]=""
	pkg=_setDetailFromAppstream(app,pkg)
	pkg['categories']=app.get_categories()
	pkg['license']=app.get_project_license()
	pkg['screenshots']=_getScreenshotsFromAppstream(app)
	return(pkg)
#def _appstreamAppToRebost

def appstreamToRebost(appstreamApps):
	rebostPkgList=[]
	if not isinstance(appstreamApps,list) and appstreamApps!=None:
		appstreamApps=[appstreamApps]
	while appstreamApps:
		app=appstreamApps.pop(0)
		rebostPkg=_appstreamAppToRebost(app)
		if rebostPkg.get("id","")!="":
			rebostPkgList.append(rebostPkg)
	return(rebostPkgList)
#def appstreamToRebost
