#!/usr/bin/env python3
import os
import html2text
import gi
gi.require_version('AppStream', '1.0')
from gi.repository import AppStream as appstream
import sqlite3
import json
import html
import logging

DBG=True

def _debug(msg):
	if DBG:
		logging.warning("rebostHelper: %s"%str(msg))
	
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
	table=table.replace('.db','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table.replace('.db',''))
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
#def rebostPkgList_to_sqlite

def rebostPkg_to_sqlite(rebostPkg,table):
	db=sqlite3.connect(table)
	table=table.replace('.db','')
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
#def _sanitizeString

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
				versionArray=["0.0"]
				for release in component.get_releases():
					versionArray.append(release.get_version())
				pkg['versions']={'flatpak':versionArray[-1]}

		rebostPkgList.append(pkg)
	return(rebostPkgList)
#def appstream_to_rebost

def generate_epi_for_rebostpkg(rebostpkg,bundle):
	if isinstance(rebostpkg,str):
		rebostpkg=json.loads(rebostpkg)
	_debug("Generating EPI for:\n{}".format(rebostpkg))
	epijson=_generate_epi_json(rebostpkg)
	episcript=_generate_epi_sh(rebostpkg,bundle)
	return(epijson)
	
def _generate_epi_json(rebostpkg):
	tmpDir="/tmp"
	epiJson="{}.epi".format(os.path.join(tmpDir,rebostpkg.get('pkgname')))
	epiFile={}
	epiFile["type"]="file"
	epiFile["pkg_list"]=[{"name":rebostpkg.get('pkgname'),'url_download':'/tmp','version':{'all':rebostpkg.get('name')}}]
	epiFile["script"]={"name":"{}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname'))),'remove':True}
	epiFile["required_root"]=True
	epiFile["download"]=True
	epiFile["required_dconf"]=True

	try:
		with open(epiJson,'w') as f:
			json.dump(epiFile,f,indent=4)
	except Exception as e:
		_debug("%s"%e)
		retCode=1
	return(epiJson)

def _generate_epi_sh(rebostpkg,bundle):
	tmpDir="/tmp"
	epiScript="{}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname')))
	try:
		if bundle=='package':
			_make_deb_script(rebostpkg,epiScript)
		if bundle=='snap':
			_make_snap_script(rebostpkg,epiScript)
		if bundle=='flatpak':
			_make_flatpak_script(rebostpkg,epiScript)
		if bundle=='appimage':
			_make_appimage_script(rebostpkg,epiScript)
	except Exception as e:
		_debug("%s"%e)
		retCode=1
	if os.path.isfile(epiScript):
		os.chmod(epiScript,0o755)
#def _generate_epi_sh

def _make_deb_script(rebostpkg,epiScript):
	_debug("Generating deb script for:\n{}".format(rebostpkg))
	with open(epiScript,'w') as f:
		f.write("#!/bin/bash\n")
		f.write("ACTION=\"$1\"\n")
		f.write("case $ACTION in\n")
		f.write("\tremove)\n")
		f.write("\t\tapt-get remove -y %s\n"%rebostpkg['pkgname'])
		f.write("\t\tTEST=$( dpkg-query -s  %s 2> /dev/null| grep Status | cut -d \" \" -f 4 )\n"%rebostpkg['pkgname'])
		f.write("\t\tif [ \"$TEST\" == 'installed' ];then\n")
		f.write("\t\t\texit 1\n")
		f.write("\t\tfi\n")
		f.write("\t\t;;\n")
		f.write("\ttestInstall)\n")
		f.write("\t\tapt-get update>/dev/null\"\"\n")
		f.write("\t\tRES=$(apt-get --simulate install %s 2>/tmp/err | awk 'BEGIN {sw=\"\"}{ver=0;if ($0~\" : \") sw=1; if ($0~\"[(]\") ver=1;if (sw==1 && ver==1) { print $0 } else if (sw==1) { print $1\" \"$2\" ( ) \"$3\" \"$4\" \"$5} }' | sed 's/.*: \(.*)\) .*/\\1/g;s/( *)//')\n"%deb)
                        
		f.write("\t\t[ -s /tmp/err ] && RES=${RES//$'\\n'/||}\"||\"$(cat /tmp/err) || RES=\"\"\n")
		f.write("\t\techo \"${RES}\"\n")
		f.write("\t\t;;\n")
		f.write("\tgetInfo)\n")
		f.write("\t\techo \"%s\"\n"%rebostpkg['description'])
		f.write("\t\t;;\n")
		f.write("esac\n")
		f.write("exit 0\n")
#def _make_deb_script

def _make_snap_script(rebostpkg,epiScript):
	_debug("Generating snap script for:\n{}".format(rebostpkg))
	with open(epiScript,'w') as f:
		f.write("#!/bin/bash\n")
		f.write("ACTION=\"$1\"\n")
		f.write("case $ACTION in\n")
		f.write("\tremove)\n")
		f.write("\t\tsnap remove %s\n"%rebostpkg['pkgname'])
		f.write("\t\t;;\n")
		f.write("\tinstallPackage)\n")
		f.write("\t\tsnap install %s\n"%rebostpkg['pkgname'])
		f.write("\t\t;;\n")
		f.write("\ttestInstall)\n")
		f.write("\t\techo \"0\"\n")
		f.write("\t\t;;\n")
		f.write("\tgetInfo)\n")
		f.write("\t\techo \"%s\"\n"%rebostpkg['description'])
		f.write("\t\t;;\n")
		f.write("esac\n")
		f.write("exit 0\n")
