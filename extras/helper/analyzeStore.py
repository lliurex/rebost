#!/usr/bin/python3
#License GPL-3  https://www.gnu.org/licenses/gpl-3.0.html 
#Copyright 2026 LliureX Team

'''This script loads the appsedu data file from rebost cache
and parses the content setting a score for the data quality

100 -> An app could be directly resolved with the included info
90 -> Included info fails for matching but there's valid column-8 data
80 -> App could be loaded through an alias
70 -> Appsedu claims app's state differs from rebost but could be resolved
60 -> App could not be resolved
50 -> App could not be resolved, and has a colum-8 that also could not be resolved
30 -> App has an unresolvable alias
20 -> App has insufficient data in any field
10 -> App has not data in any field
0 -> App only has name
'''

import os,json,sys,signal
from rebost import store
from bs4 import BeautifulSoup as bs

def _debug(msg):
	if dbg==True:
		print(msg)
#def _debug(msg):

def _print(msg):
	if output==True:
		print(msg)
#def _print(msg):

def _working(*args):
	if stop==False:
		print("\rProcessed {0}/{1}".format(processed,totalApps,end="\r"))
		signal.alarm(5)
#def _working

def _readCache():
	with open(appseduCache,"r") as f:
		rawcontent=f.read()
	bscontent=bs(rawcontent,"html.parser")
	appInfo=bscontent.find_all("td",["column-1","column-2","column-5","column-7","column-8"])
	apps=[]
	app={"name":"","icon":"","categories":"","auth":"","column8":"","href":""}
	for column in appInfo:
		full=False
		if (column.attrs["class"][0]=="column-1"):
			app["icon"]=column.img
		if (column.attrs["class"][0]=="column-2"):
			app["name"]=column.text
			href=column.find_all("a",href=True)
			for data in href:
				app["href"]=data["href"]
			_debug(app["href"])
		if (column.attrs["class"][0]=="column-5"):
			app["categories"]=column.text
		if (column.attrs["class"][0]=="column-7"):
			app["auth"]=column.text
		if (column.attrs["class"][0]=="column-8"):
			app["column8"]=column.text
			#if len(app["categories"].strip())>0:
			full=True
		if full==True:
			apps.append(app)
			app={"name":"","icon":"","categories":"","auth":"","column8":"","href":""}
			continue
	return(apps)
#def _readCache

def _analyzeApp(app):
	_debug("Analyze {}".format(app["name"]))
	href=os.path.basename(app["href"].removesuffix("/"))
	if "botiga" not in app["auth"].lower():
		if app["auth"] not in result["auth"].keys():
			result["auth"][app["auth"]]={}
		result["auth"][app["auth"]].update({app["name"]:app["href"]})
	else:
		if app["name"].lower() in appMap["nodisplay"]:
			result["nodisplay"].update({app["name"]:app["href"]})
			score[30].append(app)
		elif app["column8"] in appMap["nodisplay"]:
			result["nodisplay8"].update({app["name"]:"{} || {}".format(app["column8"],app["href"])})
			score[20].append(app)
		elif href in appMap["nodisplay"]:
			result["nodisplayHref"].update({app["name"]:"{} || {}".format(href,app["href"])})
			score[10].append(app)
		elif app["name"].lower() in appMap["aliases"].keys():
			alias=appMap["aliases"][app["name"].lower()]
			result["aliases"].update({app["name"]:"{} || {}".format(alias,app["href"])})
			app["key"]=alias
			score[60].append(app)
		elif app["column8"] in appMap["aliases"].keys():
			alias=appMap["aliases"][app["column8"]]
			result["aliases8"].update({app["name"]:"{} || {} || {}".format(app["column8"],alias,app["href"])})
			app["key"]=alias
			score[50].append(app)
		elif href in appMap["aliases"].keys():
			alias=appMap["aliases"][href]
			result["aliasesHref"].update({app["name"]:"{} || {} || {}".format(href,alias,app["href"])})
			app["key"]=alias
			score[40].append(app)
		else:
			res=json.loads(rebost.showApp(app["name"].lower()))
			if len(res)<=0:
				if len(app["column8"])>0:
					res=json.loads(rebost.showApp(app["column8"]))
				if len(res)<=0:
					res=json.loads(rebost.showApp(href))
					if len(res)<=0:
							heur=app["column8"].removeprefix("zero:")
							heur=heur.removesuffix("-lliurex")
							res=json.loads(rebost.showApp(heur))
							if len(res)<=0:
								heur=os.path.basename(app["href"].removesuffix("/"))
								heur=heur.removesuffix("-lliurex")
								res=json.loads(rebost.showApp(heur))
								if len(res)<=0:
									result["unknown"].update({app["name"]:"{} || {}".format(app["column8"],app["href"])})
									score[0].append(app)
								else:
									result["rebost"].update({app["name"]:"{} || {} || {}".format(app["column8"],heur,app["href"])})
									if deep==True:
										res=json.loads(rebost.refreshApp(heur))
									score[40].append(res[0])
									app["key"]=heur
							else:
								result["rebost"].update({app["name"]:"{} || {} || {}".format(app["column8"],heur,app["href"])})
								if deep==True:
									res=json.loads(rebost.refreshApp(heur))
								score[40].append(res[0])
								app["key"]=heur
					else:
						result["href"].update({app["name"]:app["href"]})
						if deep==True:
							res=json.loads(rebost.refreshApp(href))
						score[80].append(res[0])
				else:
					if deep==True:
						res=json.loads(rebost.refreshApp(app["column8"].lower()))
					result["column8"].update({app["name"]:"{} || {}".format(app["column8"],app["href"])})
					score[90].append(res[0])
				_debug("Unknown app: {}".format(app["name"]))
			else:
				if deep==True:
					res=json.loads(rebost.refreshApp(app["name"].lower()))
				result["known"].update({app["name"]:app["href"]})
				score[100].append(res[0])
#def _analyzeApp

def _analyzeResults(score,rebost):
	global processed,totalApps
	#Scores under 40 are from discarded or unknown apps
	apps=json.loads(rebost.getApps())
	totalApps=len(apps)
	for score,apps in score.items():
		if score<40:
			rresult["discarded"].extend(apps)
			processed+=len(apps)
			#Discard
			continue
		else:
			for scoredApp in apps:
				processed+=1
				app=scoredApp
				if app.get("key","")!="":
					key=app["key"]
					#Is an appsedu app, load app from rebost
					if deep==True:
						res=json.loads(rebost.refreshApp(key))
					else:
						res=json.loads(rebost.showApp(key))
					if len(res)==0:
						rresult["unexistent"].append(app)
					else:
						try:
							app=res[0]
						except Exception as e:
							print("Error processing {}".format(key))
							print(e)
							continue
				if len(app["bundle"])==0:
					rresult["pending"].append(app)
				else:
					rresult["knowed"].append(app)
					if len(app["bundle"])==1:
						for b in app["bundle"].keys():
							if b not in rresult["onlyOne"].keys():
								rresult["onlyOne"][b]=[]
						rresult["onlyOne"][b].append(app)
					if "unknown" not in app["bundle"]:
						for b in app["bundle"].keys():
							if b not in rresult["noZmd"]:
								rresult["noZmd"][b]=[]
							rresult["noZmd"][b].append(app)
				if app["description"].count(" ")<4:
					if "appsedu" in app.get("homepage",""):
						rresult["appDetail"].append(app)
					else:
						rresult["poorDesc"].append(app)
						if app["summary"].count(" ")<2 or app["summary"]==app["description"]:
							rresult["poorSum"].append(app)
				else:
					if app["summary"].count(" ")<2 or app["summary"]==app["description"]:
						rresult["poorSum"].append(app)
				if len(app["screenshots"])==0:
					rresult["noImages"].append(app)
				if (app.get("homepage","")=="" and app.get("infopage")=="") or "github.com/lliurex" in app.get("homepage",""):
					rresult["noUrl"].append(app)
	for key,items in rresult.items():
		_print("{} ({})".format(key,len(items)))
#def _analyzeResults
				

def _addStoreButton(app):
	button="&nbsp&nbsp&nbsp<a href=\"appstream://{}\"><button>Store</button></a>".format(app)
	return(button)
#def _addStoreButton

def _writeHtmlHeader(f):
	f.write("<HTML>")
	f.write("<BODY>")
	f.write("<h1 id=\"rindex\">REBOST STADISTICS</h1>")
	f.write("<pre>The different sections are not exclusive and an app could be in more than one</pre>")
	_writeRebostIndex(f,rresult)
	f.write("<h1 id=\"index\">APPSEDU DATA</h1>")
	f.write("<pre>The different sections are mutually exclusive for apps</pre>")
	_writeAppseduIndex(f,result)
#def _writeHtmlHeader

def _writeAppseduIndex(f,results):
	f.write("<ol>")
	f.write('<li title=\"{1}\"><a href="#known">Apps well known ({0})</a></li>'.format(len(results["known"]),tooltips["known"]));
	f.write('<li title=\"{1}\"><a href="#column8">Apps finded by column8 ({0})</a></li>'.format(len(results["column8"]),tooltips["column8"]));
	f.write('<li title=\"{1}\"><a href="#href">Apps finded by href detail ({0})</a></li>'.format(len(results["href"]),tooltips["href"]));
	f.write('<li title=\"{1}\"><a href="#aliased">Apps finded by custom map ({0})</a></li>'.format(len(results["aliases"]),tooltips["aliased"]));
	f.write('<li title=\"{1}\"><a href="#aliased8">Apps finded by custom map through column8 ({0})</a></li>'.format(len(results["aliases8"]),tooltips["aliased8"]));
	f.write('<li title=\"{1}\"><a href="#aliasedHref">Apps finded by custom map through href detail {0})</a></li>'.format(len(results["aliasesHref"]),tooltips["aliasedhref"]));
	f.write('<li title=\"{1}\"><a href="#rebost">Apps finded using Rebost heuristics {0})</a></li>'.format(len(results["rebost"]),tooltips["rebost"]));
	f.write('<li title=\"{1}\"><a href="#noauth">Apps with auth other than <em>Autoritzada-Botiga</em> ({0} cases)</a></li>'.format(len(results["auth"]),tooltips["noauth"]));
	f.write('<ul>')
	for key,val in results["auth"].items():
		f.write("<li><a href=\"#{0}\">{0} ({1})</a></li>".format(key.replace(" ","_"),len(val)));
	f.write('</ul>')
	f.write('<li><a href="#nodisplay">Apps marked as NoDisplay ({0})</a></li>'.format(len(results["nodisplay"]),tooltips["nodisplay"]));
	f.write('<li><a href="#nodisplay8">Apps marked as NoDisplay through Column8 ({0})</a></li>'.format(len(results["nodisplay8"]),tooltips["nodisplay8"]));
	f.write('<li><a href="#nodisplayHref">Apps marked as NoDisplay through href detail ({0})</a></li>'.format(len(results["nodisplayHref"]),tooltips["nodisplayhref"]));
	f.write('<li><a href="#unknown">Unknown apps ({0})</a></li>'.format(len(results["unknown"]),tooltips["unknown"]));
	f.write('</ol>')
#def _writeAppseduIndex

def _writeKnown(f,results):
	title=tooltips["known"]
	f.write("<li><h3 title=\"{1}\" id='known'>Apps well known ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["known"]),title))
	for key,href in results["known"].items():
		button=_addStoreButton(key)
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(href,key,button))
		_print("{0} || {1} ".format(key,href))
#def _writeKnown

def _writeColumn8(f,results):
	title=tooltips["column8"]
	f.write("<li><h3 title=\"{1}\" id='column8'>Apps finded through column8 ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["column8"]),title))
	for key,app in results["column8"].items():
		alias,href=app.split("||")
		button=_addStoreButton(alias)
		f.write("<a href=\"{0}\">{1}</a> -> {2}{3}<br>".format(href,key,alias,button))
		_print("{0} ({1}) || {2} ".format(key,alias,href))
#def _writeColumn8

def _writeHref(f,results):
	title=tooltips["href"]
	f.write("<li><h3 title=\"{1}\" id='href'>Apps finded through href detail ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["href"]),title))
	for key,app in results["href"].items():
		aliasHref=os.path.basename(app.removesuffix("/"))
		button=_addStoreButton(aliasHref)
		f.write("<a href=\"{0}\">{1}</a> -> {2}{3}<br>".format(app,key,aliasHref,button))
		_print("{0} ({1}) || {2} ".format(key,aliasHref,app))
#def _writeHref

def _writeAliased(f,results):
	title=tooltips["aliased"]
	f.write("<li><h3 title=\"{1}\" id='aliased'>Apps finded through custom map ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["aliases"]),title))
	for key,app in results["aliases"].items():
		alias,href=app.split("||")
		button=_addStoreButton(alias)
		f.write("<a href=\"{0}\">{1}</a> -> {2}{3}<br>".format(href,key,alias,button))
		_print("{0} || {1} ".format(key,app))
#def _writeAliased

def _writeAliased8(f,results):
	title=tooltips["aliased8"]
	f.write("<li><h3 title=\"{1}\" id='aliased8'>Column8 finded through custom map ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["aliases8"]),title))
	for key,app in results["aliases8"].items():
		alias,column8,href=app.split("||")
		button=_addStoreButton(alias)
		f.write("<a href=\"{0}\">{1} ({3})</a> -> {2}{4}<br>".format(href,key,alias,column8,button))
		_print("{0} || {1} ".format(key,app))
#def _writeAliased8(f,results):

def _writeAliasedHref(f,results):
	title=tooltips["aliasedhref"]
	f.write("<li><h3 title=\"{1}\" id='aliasedHref'>Detail href finded through custom map ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["aliasesHref"]),title))
	for key,app in results["aliasesHref"].items():
		column8,alias,href=app.split("||")
		button=_addStoreButton(alias.strip())
		f.write("<a href=\"{0}\">{1} ({2})</a> -> {3}{4}<br>".format(href,key,column8,alias,button))
		_print("{0} || {1} ".format(key,app))
#def _writeAliasedHref(f,results):

def _writeRebost(f,results):
	title=tooltips["rebost"]
	f.write("<li><h3 title=\"{1}\" id='rebost'>Apps find using heuristics from Rebost ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["aliasesHref"]),title))
	for key,app in results["rebost"].items():
		column8,alias,href=app.split("||")
		button=_addStoreButton(alias)
		f.write("<a href=\"{0}\">{1} ({3})</a> -> {2}{4}<br>".format(href,key,column8,alias,button))
		_print("{0} || {1} ".format(key,app))
#def _writeAliasedHref(f,results):

def _writeAuthApps(f,results):
	title=tooltips["noauth"]
	f.write("<li><h3 title=\"{1}\" id='noauth'> Apps with auth other than \"Autoritzada botiga\" ({0} cases)&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["auth"]),title))
	for key,apps in results["auth"].items():
		f.write("<h4 id={0}>{1} ({2})</h4>".format(key.replace(" ","_"),key,len(apps)))
		_print(" * {0} ({1})".format(key,len(apps)))
		for app,href in apps.items():
			f.write("<a href={0}>{1}</a><br>".format(href,app))
			_print("{0} ({1})".format(app,href))
#def _writeAuthApps

def _writeNoDisplay(f,results):
	title=tooltips["nodisplay"]
	f.write("<li><h3 title=\"{1}\" id='nodisplay'>Apps marked as NoDisplay in rebost ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["nodisplay"]),title))
	for key,app in results["nodisplay"].items():
		f.write("{0} || {1} ".format(key,app))
		_print("{0} || {1} ".format(key,app))
#def _writeNodisplay(f,results):

def _writeNoDisplay8(f,results):
	title=tooltips["nodisplay8"]
	f.write("<li><h3 title=\"{1}\" id='nodisplay8'>Column8 marked as NoDisplay in rebost ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["nodisplay8"]),title))
	for key,app in results["nodisplay8"].items():
		column8,href=app.split("||")
		f.write("<a href=\"{0}\">{1}</a> -> {2}<br>".format(href,key,column8))
		_print("{0} || {1} ".format(key,app))
#def _writeNoDisplay8(f,results):

def _writeNoDisplayHref(f,results):
	title=tooltips["nodisplayhref"]
	f.write("<li><h3 title=\"{1}\" id='nodisplay8'>Detail href marked as NoDisplay in rebost ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["nodisplayHref"]),title))
	for key,app in results["nodisplayHref"].items():
		column8,href=app.split("||")
		f.write("<a href=\"{0}\">{1}</a> -> {2}<br>".format(href,key,column8))
		_print("{0} || {1} ".format(key,app))
#def _writeNoDisplayHref(f,results):

def _writeUnknown(f,results):
	title=tooltips["unknown"]
	f.write("<li><h3 title=\"{1}\" id='unknown'>Unknown Apps ({0})&nbsp&nbsp&nbsp<a href=\"#index\"><button>Return</button></a></li></h3>".format(len(results["unknown"]),title))
	for key,app in results["unknown"].items():
		column8,href=app.split("||")
		f.write("<a href=\"{1}\">{0} ({2})</a><br>".format(key,href,column8))
		_print("{0} || {1} ".format(key,app))
#def _writeUnknown

def _endHtmlDoc(f):
	f.write("</BODY>")
	f.write("</HTML>")
#def _endHtml(f):

def _writeAppseduResults(results):
	f.write("<hr>")
	f.write("<h2>Appsedu analytics</h2>")
	f.write("Total apps: {0}. Proccesed {1}".format(len(apps),processed))
	f.write("<ul>")
	_print("==================================")
	_print(" ** Well known apps ({0}) **".format(len(results["known"])))
	_writeKnown(f,results)
	_print(" ** Apps finded using column8 ({0}) **".format(len(results["column8"])))
	_writeColumn8(f,results)
	_print(" ** Apps finded using href of detail ({0}) **".format(len(results["href"])))
	_writeHref(f,results)
	_print(" ** Custom mapped Apps ({0}) **".format(len(results["aliases"])))
	_writeAliased(f,results)
	_print(" ** Custom mapped column8 ({0}) **".format(len(results["aliases8"])))
	_writeAliased8(f,results)
	_print(" ** Custom mapped detail href ({0}) **".format(len(results["aliasesHref"])))
	_writeAliasedHref(f,results)
	_print(" ** Apps finded through rebost heuristics {0}) **".format(len(results["rebost"])))
	_writeRebost(f,results)
	_print(" ** Apps with auth other than \"Autoritzada botiga\" **")
	_writeAuthApps(f,results)
	_print(" ** Apps marked as NoDisplay in rebost ({0}) **".format(len(results["nodisplay"])))
	_writeNoDisplay(f,results)
	_print(" ** Column8 marked as NoDisplay in rebost ({0}) **".format(len(results["nodisplay8"])))
	_writeNoDisplay8(f,results)
	_print(" ** Detail href marked as NoDisplay in rebost ({0}) **".format(len(results["nodisplay8"])))
	_writeNoDisplayHref(f,results)
	_print(" ** Unknown Apps ({0}) **".format(len(results["unknown"])))
	_writeUnknown(f,results)
	f.write("</ul>")
	f.write("Total apps: {0}. Proccesed {1}".format(len(apps),processed))
#def _writeAppseduResults

def _writeRebostIndex(f,results):
	f.write("<ol>")
	cont=0
	for b,apps  in results["onlyOne"].items():
		cont+=len(apps)
	f.write('<li title=\"{1}\"><a href="#onlyone">Apps with only one install option ({0})</a></li>'.format(cont,tooltips["onlyone"]));
	cont=0
	for b,apps  in results["noZmd"].items():
		cont+=len(apps)
	f.write('<li title=\"{1}\"><a href="#nozmd">Apps not distributed as Zomandos ({0})</a></li>'.format(cont,tooltips["nozmd"]));
	f.write('<li title=\"{1}\"><a href="#unexistent">Apps without install options ({0})</a></li>'.format(len(results["unexistent"]),tooltips["unexistent"]))
	f.write('<li title=\"{1}\"><a href="#discarded">Apps discarded ({0})</a></li>'.format(len(results["discarded"]),tooltips["discarded"]))
	f.write('<li title=\"{1}\"><a href="#appdetail">Apps needing details from appsedu ({0})</a></li>'.format(len(results["appDetail"]),tooltips["appdetail"]))
	f.write('<li title=\"{1}\"><a href="#poordesc">Apps with bad description ({0})</a></li>'.format(len(results["poorDesc"]),tooltips["poordesc"]))
	f.write('<li title=\"{1}\"><a href="#poorsum">Apps with bad summary ({0})</a></li>'.format(len(results["poorSum"]),tooltips["poorsum"]))
	f.write('<li title=\"{1}\"><a href="#noimages">Apps without screenshots ({0})</a></li>'.format(len(results["noImages"]),tooltips["noimages"]))
	f.write('<li title=\"{1}\"><a href="#nourl">Apps without URL ({0})</a></li>'.format(len(results["noUrl"]),tooltips["nourl"]))
	f.write("</ol>")
#def _writeRebostIndex

def _writeRebostOnlyOne(f,results):
	title=tooltips["onlyone"]
	f.write("<h3 title=\"{1}\" id='onlyone'>Apps with only one bundle ({0} types)&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["onlyOne"]),title))
	f.write("<ul>")
	for bundle,apps in results["onlyOne"].items():
		f.write("<li><h4 id=\"#{0}\">{0} ({1})</h4></li>".format(bundle.replace("unknown","zomando"),len(apps)))
		for app in apps:
			button=_addStoreButton(app["name"])
			f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app["homepage"],app["name"],button))
	f.write("</ul>")
#def _writeRebostOnlyOne

def _writeRebostNoZmd(f,results):
	title=tooltips["nozmd"]
	f.write("<h3 title=\"{1}\" id='nozmd'>Apps not distributed as Zomandos ({0} types)&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["noZmd"]),title))
	f.write("<ul>")
	for bundle,apps in results["noZmd"].items():
		f.write("<li><h4 id=\"#{0}\">{0} ({1})</h4></li>".format(bundle.replace("unknown","zomando"),len(apps)))
		for app in apps:
			button=_addStoreButton(app["name"])
			f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"],button))
	f.write("</ul>")
#def _writeRebostNoZmd

def _writeRebostUnexistent(f,results):
	title=tooltips["unexistent"]
	f.write("<h3 title=\"{1}\" id='unexistent'>Apps without install options ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["unexistent"]),title))
	for app in results["unexistent"]:
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"]))
#def _writeRebostUnexistent

def _writeRebostDiscarded(f,results):
	title=tooltips["discarded"]
	f.write("<h3 title=\"{1}\" id='discarded'>Apps from appsedu discarded ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["discarded"]),title))
	for app in results["discarded"]:
		f.write("<a href=\"{0}\">{1}</a><br>".format(app.get("homepage","https://github.com/lliurex"),app["name"]))
#def _writeRebostDiscarded

def _writeRebostAppDetail(f,results):
	title=tooltips["appdetail"]
	f.write("<h3 title=\"{1}\" id='appdetail'>Apps needing info from appsedu ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["appDetail"]),title))
	for app in results["appDetail"]:
		button=_addStoreButton(app["name"])
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"],button))
#def _writeRebostAppDetail

def _writeRebostPoorSum(f,results):
	title=tooltips["poorsum"]
	f.write("<h3 title=\"{1}\" id='poorsum'>Apps with too short summary ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["poorSum"]),title))
	for app in results["poorSum"]:
		button=_addStoreButton(app["name"])
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"],button))
#def _writeRebostPoorSum

def _writeRebostPoorDesc(f,results):
	title=tooltips["poordesc"]
	f.write("<h3 title=\"{1}\" id='poordesc'>Apps with too short description ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["poorDesc"]),title))
	for app in results["poorDesc"]:
		button=_addStoreButton(app["name"])
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"],button))
#def _writeRebostPoorDesc

def _writeRebostNoImages(f,results):
	title=tooltips["noimages"]
	f.write("<h3 title=\"{1}\" id='noimages'>Apps without screenshots ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["noImages"]),title))
	for app in results["noImages"]:
		button=_addStoreButton(app["name"])
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"],button))
#def _writeRebostNoImages

def _writeRebostNoUrl(f,results):
	title=tooltips["nourl"]
	f.write("<h3 title=\"{1}\" id='nourl'>Apps without URL ({0})&nbsp&nbsp&nbsp<a href=\"#rindex\"><button>Return</button></a></li></h3>".format(len(results["noUrl"]),title))
	for app in results["noUrl"]:
		button=_addStoreButton(app["name"])
		f.write("<a href=\"{0}\">{1}</a>{2}<br>".format(app.get("homepage","https://github.com/lliurex"),app["name"],button))
#def _writeRebostNoImages

def _writeRebostResults(results):
	f.write("<hr>")
	f.write("<h2>Rebost analytics</h2>")
	f.write("Total apps: {0}".format(len(results["knowed"])))
	_writeRebostOnlyOne(f,results)
	_writeRebostNoZmd(f,results)
	_writeRebostUnexistent(f,results)
	_writeRebostDiscarded(f,results)
	_writeRebostAppDetail(f,results)
	_writeRebostPoorDesc(f,results)
	_writeRebostPoorSum(f,results)
	_writeRebostNoImages(f,results)
	_writeRebostNoUrl(f,results)
#def _writeRebostResults

### MAIN ###

dbg=False # for development purposes only
output=False
cache="/var/cache/rebost/raw"
appseduCache=os.path.join(cache,"appsedu.raw")
foutput="/tmp/output.html"
deep=False
signal.signal(signal.SIGALRM,_working)
signal.alarm(5)
h=False
apps=[]
processed=0
score={}

if len(sys.argv)>1:
	args=sys.argv[1:]
	args.reverse()
	while args:
		arg=args.pop()
		if arg.lower().replace("-","") in ["v","verbose"]:
			output=True
		elif arg.lower().replace("-","") in ["i","input"]:
			appseduCache=args.pop()
		elif arg.lower().replace("-","") in ["d","deep-analysis"]:
			deep=True
		elif arg.lower().replace("-","") in ["o","output"]:
			foutput=args.pop().replace(" ","_")
			if foutput.endswith(".html")==False:
				foutput+=".html"
		else:
			h=True
	if h==True:
		print("Usage:")
		print("\t{0} [-v || --verbose] [-h || --help] [-i || --input file] [-d || --deep-analysis] [-o || --output file]".format(sys.argv[0]))
		print("")
		print("\t -h --help: Show this message")
		print("\t -v --verbose: Print output")
		print("\t -i --input: file: Path to a downloaded appsedu webpage, {} by default".format(appseduCache))
		print("\t -d --deep-analysis: Refresh all info from apps before processing. Time consuming and not as good as seems")
		print("\t -o --output: file: Output file, /tmp/output.html by default")
		sys.exit(0)

stop=False
result={"known":{},
	"href":{},
	"column8":{},
	"auth":{},
	"unknown":{},
	"rebost":{},
	"aliases":{},
	"aliases8":{},
	"aliasesHref":{},
	"nodisplay":{},
	"nodisplay8":{},
	"nodisplayHref":{}
}
rresult={"knowed":[],
	"pending":[],
	"onlyOne":{},
	"noZmd":{},
	"discarded":[],
	"unexistent":[],
	"poorDesc":[],
	"poorSum":[],
	"appDetail":[],
	"noImages":[],
	"noUrl":[]
	}

tooltips={"known":"Apps matched using its own name.",
		"column8":"Apps matched using the column8 content.",
		"href":"Apps matched using the URL of the detail. This implies that name and colum8 are invalid",
		"aliased":"Apps matched using custom rebost aliases. These are errors as custom map is the last resort",
		"aliased8":"Apps matching using the value of column8 for aliases. These are errors as custom map is the last resort",
		"aliasedhref":"Apps matched using the URL of the detail for aliases. These are errors as custom map is the last resort",
		"rebost":"This apps has been finded using heuristics so cost more time",
		"noauth":"This apps has not been authorized yet or are revoked",
		"nodisplay":"Apps marked by name as nodisplay in rebost",
		"nodisplay8":"Apps marked by column8 as nodisplay in rebost",
		"nodisplayhref":"Apps marked by href as nodisplay in rebost",
		"unknown":"Ideally zero",
		"onlyone":"This apps only have one installer, this is not bad per se",
		"nozmd":"This apps are not included in zomandos, rebost picks up them from catalogues",
		"unexistent":"Apps without installer. This should not happen",
		"discarded":"Rebost has discarded thisa apps, perhaps marked as nodisplay",
		"appdetail":"Apps that requires retrieve data from appsedu portal. Time consuming, impact on GUI",
		"poorsum":"Apps with a potentially useless summary",
		"poordesc":"Apps with a potentially useless description",
		"noimages":"Apps without screenshots",
		"nourl":"Apps without homepage or infopage",
		}

if os.path.exists(appseduCache):	
	for i in range (0,110,10): 
		score[i]=[]
	try:
		apps=_readCache()
	except Exception as e:
		print("{0}: {1}".format(appseduCache,e))
	totalApps=len(apps)
	if totalApps>0:
		f=open(foutput,"w")
		rebost=store.client()
		appMap=rebost.getMaps()
		print("Analyzing appsedu data")
		deep=False
		for app in apps:
			_analyzeApp(app)
			processed+=1
		print("Completed.\nAnalyzing store data")
		processed=0
		_analyzeResults(score,rebost)
		_writeHtmlHeader(f)
		_writeAppseduResults(result)
		_writeRebostResults(rresult)
		_endHtmlDoc(f)
		f.close()
		print("Completed.")
		print("-------========-------")
		print("Output file generated: {}".format(foutput))
else:
	print("Could not find input file {}".format(appseduCache))

sys.exit(0)
