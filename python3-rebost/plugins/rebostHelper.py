#!/usr/bin/env python3
import os
import html2text
import gi
gi.require_version('AppStream', '1.0')
from gi.repository import AppStream as appstream
import sqlite3
import json
import html
	
def rebostProcess(*kwargs):
	reb={'plugin':'','kind':'','progressQ':'','progress':'','resultQ':'','result':'','action':'','parm':'','proc':''}
	return(reb)

def resultSet(*kwargs):
	rs={'id':'','name':'','title':'','msg':'','description':'','error':0,'errormsg':''}
	return(rs)

def rebostPkg(*kwargs):
	pkg={'name':'','id':'','size':'','screenshots':[],'video':[],'pkgname':'','description':{},'summary':{},'icon':'','size':'','downloadSize':'','bundle':{},'kind':'','version':'','versions':{},'installed':'','banner':'','license':'','homepage':'','categories':[],'installerUrl':'','state':{}}
	return(pkg)

def rebostPkgList_to_sqlite(rebostPkgList,table):
	db=sqlite3.connect(table)
	table=table.replace('.sql','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table.replace('.sql',''))
	cursor.execute(query)
	for rebostPkg in rebostPkgList:
		query="INSERT or REPLACE INTO {} (pkg,data) VALUES ('{}','{}')".format(table,rebostPkg.get('pkgname').lower(),str(json.dumps(rebostPkg)))
		try:
			cursor.execute(query)
		except Exception as e:
			print(query)
			print(e)
	db.commit()
	db.close()

def enable_connection(table):
	db=sqlite3.connect(table)
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table)
	cursor.execute(query)

def close_connection(table):
	db=sqlite3.connect(table)
	db.commit()
	db.close()

def rebostPkg_to_sqlite(rebostPkg,table):
	db=sqlite3.connect(table)
	table=table.replace('.sql','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table)
	#print(query)
	cursor.execute(query)
	query="INSERT INTO {} (pkg,data) VALUES ('{}','{}')".format(table,rebostPkg.get('pkgname').lower(),str(json.dumps(rebostPkg)))
	#print(query)
	try:
		cursor.execute(query)
	except sqlite3.OperationalError as e:
		if "locked" in e:
			time.sleep(0.1)
			cursor.execute(query)
	db.commit()
	db.close()
#def rebostPkgList_to_sqlite

def rebostPkgList_to_xml(rebostPkgList,xmlFile=None):
	resultSet=[]
	for rebostPkg in rebostPkgList:
		if xmlFile:
			baseDir=os.path.join(os.path.dirname(xmlFile))#,rebost['name'][0].lower())	
			f_file=os.path.join(baseDir,"{}.xml".format(rebost['id']))
			if not os.path.exists(baseDir):
				try:
					os.makedirs(baseDir)
				except Exception as e:
					self._debug("Error creating folder {}: {}".format(baseDir,e))
					continue
			_generateInfo(f_file,rebost)
		else:
			resultSet.append(_generateInfoMem(rebostPkg))
	return(resultSet)

def _sanitizeString(data):
	if isinstance(data,str):
		data=html2text.html2text(data,"lxml")
		data=data.replace("&","and")
		data=data.replace("\n"," ")
		data=data.replace("<","*")
		data=data.replace(">","*")
		data=data.replace("\\","*")
		data=data.replace("<p><p>","<p>")
		data=data.replace("*br*"," ")
		data=data.replace("*p*"," ")
		data=data.replace('<\p><\p>','<\p>')
	return(data)

def appstream_to_rebost(appstreamCatalogue):
	rebostPkgList=[]
	for component in appstreamCatalogue.get_apps():
		pkg=rebostPkg()
		pkg['id']=component.get_id().lower()
		pkg['name']=component.get_name().lower()
		pkg['name']=html.escape(pkg['name']).encode('ascii', 'xmlcharrefreplace').decode() 
		if component.get_pkgname_default():
			pkg['pkgname']=component.get_pkgname_default()
		else:
			candidateName=component.get_id().split(".")
			if len(candidateName)>3:
				pkg['pkgname']='-'.join(candidateName[2:])
			elif len(candidateName)>2:
				pkg['pkgname']=candidateName[-1]
			elif len(candidateName)>1:
				pkg['pkgname']=join('-').candidateName
			elif len(candidateName)>0:
				pkg['pkgname']=candidateName[0]
		#print("{} - {}".format(pkg['name'],pkg['pkgname']))
		pkg['summary']=component.get_comment()
		pkg['summary']=_sanitizeString(html2text.html2text(pkg['summary'],"lxml"))
		pkg['summary']=html.escape(pkg['summary']).encode('ascii', 'xmlcharrefreplace').decode() 
		pkg['description']=component.get_description()
		if not isinstance(pkg['description'],str):
			pkg['description']=pkg['summary']
		pkg['description']=_sanitizeString(html2text.html2text(pkg['description'],"lxml"))
		pkg['description']=html.escape(pkg['description']).encode('ascii', 'xmlcharrefreplace').decode() 
		for icon in component.get_icons():
			if icon.get_filename():
				pkg['icon']=icon.get_filename()
				break
			if icon.get_url():
				pkg['icon']=icon.get_url()
		pkg['categories']=component.get_categories()
		for i in component.get_bundles():
			if i.get_kind()==2: #appstream.BundleKind.FLATPAK:
				pkg['bundle']={'flatpak':pkg['id']}

		rebostPkgList.append(pkg)
	return(rebostPkgList)


def _generateInfoMem(rebostPkg):
	locale="C"
	xmlApp=[]
	xmlApp=['<?xml version="1.0" encoding="UTF-8"?>']
	xmlApp.append('<components>')
	xmlApp.append('<component type="desktop">')
	xmlApp.append('<id>{}</id>'.format(rebostPkg['id'].lower()))
	xmlApp.append('<name>{}</name>'.format(rebostPkg['name']))
	xmlApp.append('<pkgname>{}</pkgname>'.format(rebostPkg['pkgname']))
	if isinstance(rebostPkg['summary'],dict):
		for lang,desc in rebostPkg['summary'].items():
			desc=_sanitizeString(rebostPkg['summary'][lang])
			xmlApp.append("<summary xml:lang=\"{}\" >{}</summary>".format(lang.lower(),desc))
		idx=rebostPkg['summary'].get("C",'')
		if idx:
			desc=_sanitizeString(rebostPkg['summary']["C"])
			xmlApp.append("<summary>{}</summary>".format(desc))
		else:
			idx=list(rebostPkg['summary'].keys())[0]
			desc=_sanitizeString(rebostPkg['summary'][idx])
			xmlApp.append("<summary>{}</summary>".format(desc))
	else:
		desc=_sanitizeString(rebostPkg['summary'])
		xmlApp.append("<summary>{}</summary>".format(desc))
	if isinstance(rebostPkg['description'],dict):
		for lang,desc in rebostPkg['description'].items():
			desc=_sanitizeString(rebostPkg['description'][lang])
			xmlApp.append("<description xml:lang=\"{}\" ><p>{}</p></description>".format(lang.lower(),desc))
		idx=rebostPkg['description'].get("C",'')
		if idx:
			xmlApp.append("<description><p>{}</p></description>".format(_sanitizeString(rebostPkg['description']["C"])))
		elif rebostPkg['description']:
			idx=list(rebostPkg['description'].keys())[0]
			xmlApp.append("<description><p>{}</p></description>".format(_sanitizeString(rebostPkg['description'][idx])))
	else:
		desc=_sanitizeString(html2text.html2text(rebostPkg['description'],"lxml"))
		xmlApp.append("<description><p>{}</p></description>".format(desc))
	if rebostPkg['icon'] and os.path.isfile(rebostPkg['icon']):
		xmlApp.append('<icon type="local">{}</icon>'.format(rebostPkg['icon']))
	else:
		xmlApp.append('<icon type="stock">{}</icon>'.format(rebostPkg['icon']))
	#f_list.append('<kind>{}</kind>'.format(rebost['kind']))
	xmlApp.append('<categories>')
	added_cat=[]
	for cat in rebostPkg['categories']:
		if cat and cat.lower() not in added_cat:
			xmlApp.append('<category>{}</category>'.format(cat))
			added_cat.append(cat.lower())
	if not added_cat:
		xmlApp.append('<category>Utility</category>')
	xmlApp.append('</categories>')
	xstatus={}
	if rebostPkg["bundle"]:
		bundlePkg=''
		if rebostPkg['installerUrl']:
				#bundlePkg=rebost['installerUrl']
			xmlApp.append('<url type="unknown">{}</url>'.format(rebostPkg['installerUrl']))
		for bundle,desc in rebostPkg["bundle"].items():
			if bundlePkg=='':
				bundlePkg=desc
			xmlApp.append("<bundle type=\"{}\">{}</bundle>".format(bundle,bundlePkg))

	if rebostPkg['homepage']:
		xmlApp.append('<url type="homepage">{}</url>'.format(rebostPkg['homepage']))
	if rebostPkg['version']:
		xmlApp.append("<releases><release version=\"{}\"/></releases>".format(rebostPkg["version"]))

	xmlApp.append('</component>')
	xmlApp.append('</components>')
	xml="".join(xmlApp)
	return (xml)

def _generateInfo(f_file,rebost):
	#
	if rebost.get('version'):
		if os.path.isfile(f_file):
			with open (f_file,'r') as f:
				for l in f.readlines():
						if rebost.get('version') in l:
							return

	locale="C"
	f_list=[]
	f_list=['<?xml version="1.0" encoding="UTF-8"?>']
	f_list.append('<components>')
	f_list.append('<component type="desktop">')
	f_list.append('<id>{}</id>'.format(rebost['id'].lower()))
	f_list.append('<name>{}</name>'.format(rebost['name']))
	f_list.append('<pkgname>{}</pkgname>'.format(rebost['pkgname']))
	if isinstance(rebost['summary'],dict):
		for lang,desc in rebost['summary'].items():
			desc=_sanitizeString(rebost['summary'][lang])
			f_list.append("<summary xml:lang=\"{}\" >{}</summary>".format(lang.lower(),desc))
		idx=rebost['summary'].get("C",'')
		if idx:
			desc=_sanitizeString(rebost['summary']["C"])
			f_list.append("<summary>{}</summary>".format(desc))
		else:
			idx=list(rebost['summary'].keys())[0]
			desc=_sanitizeString(rebost['summary'][idx])
			f_list.append("<summary>{}</summary>".format(desc))
	else:
		desc=_sanitizeString(rebost['summary'])
		f_list.append("<summary>{}</summary>".format(desc))
	if isinstance(rebost['description'],dict):
		for lang,desc in rebost['description'].items():
			desc=_sanitizeString(rebost['description'][lang])
			f_list.append("<description xml:lang=\"{}\" ><p>{}</p></description>".format(lang.lower(),desc))
		idx=rebost['description'].get("C",'')
		if idx:
			f_list.append("<description><p>{}</p></description>".format(_sanitizeString(rebost['description']["C"])))
		elif rebost['description']:
			idx=list(rebost['description'].keys())[0]
			f_list.append("<description><p>{}</p></description>".format(_sanitizeString(rebost['description'][idx])))
	else:
		desc=_sanitizeString(html2text.html2text(rebost['description'],"lxml"))
		f_list.append("<description><p>{}</p></description>".format(desc))
	if rebost['icon'] and os.path.isfile(rebost['icon']):
		f_list.append('<icon type="local">{}</icon>'.format(rebost['icon']))
	else:
		f_list.append('<icon type="stock">{}</icon>'.format(rebost['icon']))
	#f_list.append('<kind>{}</kind>'.format(rebost['kind']))
	f_list.append('<categories>')
	added_cat=[]
	for cat in rebost['categories']:
		if cat and cat.lower() not in added_cat:
			f_list.append('<category>{}</category>'.format(cat))
			added_cat.append(cat.lower())
	if not added_cat:
		f_list.append('<category>Utility</category>')
	f_list.append('</categories>')
	xstatus={}
	if rebost["bundle"]:
		bundlePkg=''
		if rebost['installerUrl']:
				#bundlePkg=rebost['installerUrl']
			f_list.append('<url type="unknown">{}</url>'.format(rebost['installerUrl']))
		for bundle,desc in rebost["bundle"].items():
			if bundlePkg=='':
				bundlePkg=desc
			f_list.append("<bundle type=\"{}\">{}</bundle>".format(bundle,bundlePkg))

	if rebost['homepage']:
		f_list.append('<url type="homepage">{}</url>'.format(rebost['homepage']))
	if rebost['version']:
		f_list.append("<releases><release version=\"{}\"/></releases>".format(rebost["version"]))

	f_list.append('</component>')
	f_list.append('</components>')
	try:
		with open(f_file,'w') as f:
			f.writelines(f_list)
	except Exception as e:
		print("File {} error:{}".format(f_file,e))

