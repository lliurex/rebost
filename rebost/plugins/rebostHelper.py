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
import tempfile
import subprocess

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
	pkg={'name':'','id':'','size':'','screenshots':[],'video':[],'pkgname':'','description':{},'summary':{},'icon':'','size':{},'downloadSize':'','bundle':{},'kind':'','version':'','versions':{},'installed':'','banner':'','license':'','homepage':'','categories':[],'installerUrl':'','state':{}}
	return(pkg)

def rebostPkgList_to_sqlite(rebostPkgList,table):
	wrkDir="/usr/share/rebost"
	tablePath=os.path.join(wrkDir,os.path.basename(table))
	if os.path.isfile(tablePath):
		os.remove(tablePath)
	db=sqlite3.connect(tablePath)
	table=table.replace('.db','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table.replace('.db',''))
	cursor.execute(query)
	for rebostPkg in rebostPkgList:
		name=rebostPkg.get('pkgname','').strip().lower()
		rebostPkg['summary']=_sanitizeString(rebostPkg['summary'],scape=True)
		rebostPkg['description']=_sanitizeString(rebostPkg['description'],scape=True)
		query="INSERT or REPLACE INTO {} (pkg,data) VALUES ('{}','{}')".format(table,name.lower(),str(json.dumps(rebostPkg)))
		try:
			cursor.execute(query)
		except Exception as e:
			print(query)
			print(e)
	db.commit()
	db.close()
#def rebostPkgList_to_sqlite

def rebostPkg_to_sqlite(rebostPkg,table):
	wrkDir="/usr/share/rebost"
	tablePath=os.path.join(wrkDir,os.path.basename(table))
	db=sqlite3.connect(tablePath)
	table=table.replace('.db','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table)
	#print(query)
	cursor.execute(query)
	name=rebostPkg.get('pkgname','').rstrip().lower()
	rebostPkg['summary']=_sanitizeString(rebostPkg['summary'])
	rebostPkg['description']=_sanitizeString(rebostPkg['description'])
	query="INSERT INTO {} (pkg,data) VALUES ('{}','{}')".format(table,name,str(json.dumps(rebostPkg)))
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

def _sanitizeString(data,scape=False):
	if isinstance(data,str):
		data=html2text.html2text(data)#,"lxml")
		data=data.replace("&","and")
		#data=data.replace("\n"," ")
		#data=data.replace("<","*")
		#data=data.replace(">","*")
		data=data.replace("\\","*")
		#data=data.replace("<p><p>","<p>")
		#data=data.replace("*br*","\n")
		#data=data.replace("*p*"," ")
		#data=data.replace('<\p><\p>','<\p>')
		#data=data.replace("''","'")
		#data=data.replace("'","''")
		data.rstrip()
		if scape:
			data=html.escape(data).encode('ascii', 'xmlcharrefreplace').decode() 
	return(data)
#def _sanitizeString

def appstream_to_rebost(appstreamCatalogue):
	rebostPkgList=[]
	for component in appstreamCatalogue.get_apps():
		pkg=rebostPkg()
		pkg['id']=component.get_id().lower()
		pkg['name']=_sanitizeString(component.get_name().lower().strip(),scape=True)
		#pkg['name']=html.escape(pkg['name']).encode('ascii', 'xmlcharrefreplace').decode().strip()
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
		pkg['pkgname']=pkg['pkgname'].strip().replace("-desktop","")
		pkg['summary']=component.get_comment()
		pkg['summary']=_sanitizeString(pkg['summary'],scape=True)
		pkg['description']=component.get_description()
		if not isinstance(pkg['description'],str):
			pkg['description']=pkg['summary']
		else:
			pkg['description']=_sanitizeString(pkg['description'],scape=True)
		for icon in component.get_icons():
			if icon.get_filename():
				pkg['icon']=icon.get_filename()
				break
			if icon.get_url():
				pkg['icon']=icon.get_url()
		pkg['categories']=component.get_categories()
		for i in component.get_bundles():
			if i.get_kind()==2: #appstream.BundleKind.FLATPAK:
				pkg['bundle']={'flatpak':component.get_id().replace('.desktop','')}
				versionArray=["0.0"]
				for release in component.get_releases():
					versionArray.append(release.get_version())
				pkg['versions']={'flatpak':versionArray[-1]}

		rebostPkgList.append(pkg)
	return(rebostPkgList)
#def appstream_to_rebost

def generate_epi_for_rebostpkg(rebostpkg,bundle,user=''):
	if isinstance(rebostpkg,str):
		rebostpkg=json.loads(rebostpkg)
	#_debug("Generating EPI for:\n{}".format(rebostpkg))
	_debug("Generate EPI for package {} bundle {}".format(rebostpkg.get('pkgname'),bundle))
	epijson=_generate_epi_json(rebostpkg,bundle)
	episcript=_generate_epi_sh(rebostpkg,bundle,user)
	return(epijson,episcript)
	
def _generate_epi_json(rebostpkg,bundle):
	tmpDir="/tmp"
	epiJson="{}_{}.epi".format(os.path.join(tmpDir,rebostpkg.get('pkgname')),bundle)
	if not os.path.isfile(epiJson):
		name=rebostpkg.get('name').strip()
		pkgname=rebostpkg.get('pkgname').strip()
		icon=rebostpkg.get('icon','')
		iconFolder=''
		if icon:
			iconFolder=os.path.dirname(icon)
			icon=os.path.basename(icon)
		epiFile={}
		epiFile["type"]="file"
		epiFile["pkg_list"]=[{"name":rebostpkg.get('pkgname'),"key_store":rebostpkg.get('pkgname'),'url_download':'','custom_icon':icon,'version':{'all':rebostpkg.get('name')}}]
		epiFile["script"]={"name":"{}_{}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname')),bundle),'download':True,'remove':True,'getStatus':True,'getInfo':True}
		epiFile["custom_icon_path"]=iconFolder
		epiFile["required_root"]=True
		epiFile["check_zomando_state"]=False

		try:
			with open(epiJson,'w') as f:
				json.dump(epiFile,f,indent=4)
		except Exception as e:
			_debug("%s"%e)
			retCode=1
	return(epiJson)

def _generate_epi_sh(rebostpkg,bundle,user=''):
	tmpDir="/tmp"
	epiScript="{}_{}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname')),bundle)
	if not os.path.isfile(epiScript):
		try:
			_make_epi_script(rebostpkg,epiScript,bundle,user)
		except Exception as e:
			_debug("%s"%e)
			retCode=1
		if os.path.isfile(epiScript):
			os.chmod(epiScript,0o755)
	return(epiScript)
#def _generate_epi_sh

def _make_epi_script(rebostpkg,epiScript,bundle,user=''):
	_debug("Generating script for:\n{} - {}".format(rebostpkg,bundle))
	commands=_get_bundle_commands(bundle,rebostpkg,user)

	with open(epiScript,'w') as f:
		f.write("#!/bin/bash\n")
		f.write("function getStatus()\n{")
		f.write("\t\t{}\n".format(commands.get('statusTestLine')))
		f.write("\t\tif [ \"$TEST\" == 'installed' ];then\n")
		f.write("\t\t\tINSTALLED=0\n")
		f.write("\t\telse\n")
		f.write("\t\t\tINSTALLED=1\n")
		f.write("\t\tfi\n")
		f.write("}\n")
		f.write("ACTION=\"$1\"\n")
		f.write("case $ACTION in\n")
		f.write("\tremove)\n")
		f.write("\t\t{}\n".format(commands.get('removeCmd')))
		for command in commands.get('removeCmdLine',[]):
			f.write("\t\t{}\n".format(command))
		f.write("\t\t;;\n")
		f.write("\tinstallPackage)\n")
		f.write("\t\t{}\n".format(commands.get('installCmd')))
		for command in commands.get('installCmdLine',[]):
			f.write("\t\t{}\n".format(command))
		f.write("\t\t;;\n")
		f.write("\ttestInstall)\n")	
		f.write("\t\techo \"0\"\n")
		f.write("\t\t;;\n")
		f.write("\tgetInfo)\n")
		f.write("\t\techo \"%s\"\n"%rebostpkg['description'])
		f.write("\t\t;;\n")
		f.write("\tgetStatus)\n")
		f.write("\t\tgetStatus\n")
		f.write("\t\techo $INSTALLED\n")
		f.write("\t\t;;\n")
		f.write("\tdownload)\n")
		f.write("\t\techo \"Installing...\"\n")
		f.write("\t\t;;\n")
		f.write("esac\n")
		f.write("exit 0\n")
#def _make_epi_script

def _get_bundle_commands(bundle,rebostpkg,user=''):
	commands={}
	installCmd=''
	installCmdLine= []
	removeCmd=''
	removeCmdLine=[]
	statusTestLine=''
	if bundle=='package':
		installCmd="apt-get install -y {}".format(rebostpkg['pkgname'])
		removeCmd="apt-get remove -y {}".format(rebostpkg['pkgname'])
		removeCmdLine.append("TEST=$( dpkg-query -s  %s 2> /dev/null| grep Status | cut -d \" \" -f 4 )")
		removeCmdLine.append("if [ \"$TEST\" == 'installed' ];then")
		removeCmdLine.append("exit 1")
		removeCmdLine.append("fi")
		statusTestLine=("TEST=$( dpkg-query -s  {} 2> /dev/null| grep Status | cut -d \" \" -f 4 )".format(rebostpkg['pkgname']))
	elif bundle=='snap':
		installCmd="snap install {}".format(rebostpkg['bundle']['snap'])
		removeCmd="snap remove {}".format(rebostpkg['bundle']['snap'])
		statusTestLine=("TEST=$( snap list 2> /dev/null| grep {} >/dev/null && echo 'installed')".format(rebostpkg['bundle']['snap']))
	elif bundle=='flatpak':
		installCmd="flatpak -y install {}".format(rebostpkg['bundle']['flatpak'])
		removeCmd="flatpak -y uninstall {}".format(rebostpkg['bundle']['flatpak'])
		statusTestLine=("TEST=$( flatpak list 2> /dev/null| grep $'{}\\t' >/dev/null && echo 'installed')".format(rebostpkg['bundle']['flatpak']))
	elif bundle=='appimage':
		installCmd="wget -O /tmp/{}.appimage {}".format(rebostpkg['pkgname'],rebostpkg['bundle']['appimage'])
		if user:
			installCmdLine.append("mv /tmp/{}.appimage /home/{}/.local/bin/".format(rebostpkg['pkgname'],user))
			installCmdLine.append("chown {}:{} /home/{}/.local/bin/{}.appimage".format(user,user,user,rebostpkg['pkgname']))
			installCmdLine.append("chmod +x /home/{}/.local/bin/{}.appimage".format(user,rebostpkg['pkgname']))
			removeCmd="rm /home/{}/.local/bin/{}.appimage".format(user,rebostpkg['pkgname'])
			statusTestLine=("TEST=$( ls /home/{}/.local/bin/{}.appimage  1>/dev/null 2>&1 && echo 'installed')".format(user,rebostpkg['pkgname']))
		else:
			destdir="/opt/appimages"
			if user:
				destdir=os.path.join("/home",user,".local/bin")
			destPath=os.path.join(destdir,"{}.appimage".format(rebostpkg['pkgname']))
			installCmdLine.append("mv /tmp/{0}.appimage {1}".format(rebostpkg['pkgname'],destdir))
			installCmdLine.append("chmod +x {}".format(destPath))
			installCmdLine.append("chown {0}:{0} {1}".format(user,destPath))
			removeCmd="rm {}".format(destPath)
			statusTestLine=("TEST=$( ls {}  1>/dev/null 2>&1 && echo 'installed')".format(destPath))
	commands['installCmd']=installCmd
	commands['installCmdLine']=installCmdLine
	commands['removeCmd']=removeCmd
	commands['removeCmdLine']=removeCmdLine
	commands['statusTestLine']=statusTestLine
	return(commands)

def get_epi_status(episcript):
	proc=subprocess.run([episcript,'getStatus'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	return(proc.stdout.decode().strip())

def check_remove_unsure(package):
	sw=False
	_debug("Checking if remove {} is unsure".format(package))
	proc=subprocess.run(["apt-cache","rdepends",package],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	llx=subprocess.run(["lliurex-version","-f"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	version=llx.stdout.decode().strip()
	for depend in proc.stdout.decode().split("\n"):
		if "lliurex-meta-{}".format(version) in depend:
			sw=True
			break
	_debug(proc.stdout)
	_debug("Checked")
	return(sw)
