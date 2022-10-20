#!/usr/bin/env python3
import os,shutil
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
import time

DBG=False
path="/var/log/rebost.log"
fname = "rebost.log"
logger = logging.getLogger(fname)
formatter = logging.Formatter('%(asctime)s %(message)s')
fh=logging.FileHandler(path)
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

def setDebugEnabled(dbg):
	DBG=dbg
	if DBG:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)
#def enableDbg

setDebugEnabled(DBG)


def logmsg(msg):
	logger.info("{}".format(msg))
#def logmsg(msg)

def _debug(msg):
	logger.debug("{}".format(msg))
#def _debug
	
def rebostProcess(*kwargs):
	reb={'plugin':'','kind':'','progressQ':'','progress':'','resultQ':'','result':'','action':'','parm':'','proc':''}
	return(reb)
#def rebostProcess

def resultSet(*kwargs):
	rs={'id':'','name':'','title':'','msg':'','description':'','error':0,'errormsg':''}
	return(rs)
#def resultSet

def rebostPkg(*kwargs):
	pkg={'name':'','id':'','size':'','screenshots':[],'video':[],'pkgname':'','description':'','summary':'','icon':'','size':{},'downloadSize':'','bundle':{},'kind':'','version':'','versions':{},'installed':{},'banner':'','license':'','homepage':'','categories':[],'installerUrl':'','state':{}}
	return(pkg)
#def rebostPkg

def rebostPkgList_to_sqlite(rebostPkgList,table,drop=True,sanitize=True):
	wrkDir="/usr/share/rebost"
	tablePath=os.path.join(wrkDir,os.path.basename(table))
	if drop:
		if os.path.isfile(tablePath):
			os.remove(tablePath)
	db=sqlite3.connect(tablePath)
	table=table.replace('.db','')
	cursor=db.cursor()
	if drop:
		query="DROP TABLE IF EXISTS {}".format(table)
		_debug("Helper: {}".format(query))
		cursor.execute(query)
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT,cat0 TEXT, cat1 TEXT, cat2 TEXT);".format(table)
		_debug("Helper: {}".format(query))
		cursor.execute(query)
	query=[]
	while rebostPkgList:
		rebostPkg=rebostPkgList.pop(0)
		query.append(_rebostPkg_fill_data(rebostPkg,sanitize))
		#take breath
		if len(rebostPkgList)%4==0:
			time.sleep(0.0002)
	if query:
		queryMany="INSERT or REPLACE INTO {} VALUES (?,?,?,?,?)".format(table)
		try:
			_debug("Helper: INSERTING {} for {}".format(len(query),table))
			cursor.executemany(queryMany,query)
		except Exception as e:
			_debug("Helper: {}".format(e))
		db.commit()
	db.close()
	cursor=None
	return()
#def rebostPkgList_to_sqlite

def rebostPkg_to_sqlite(rebostPkg,table):
	wrkDir="/usr/share/rebost"
	tablePath=os.path.join(wrkDir,os.path.basename(table))
	db=sqlite3.connect(tablePath)
	table=table.replace('.db','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT,cat0 TEXT,cat1 TEXT, cat2 TEXT);".format(table)
	#print(query)
	cursor.execute(query)
	query=_rebostPkg_fill_data(rebostPkg)
	if query:
		queryMany="INSERT or REPLACE INTO {} VALUES (?,?,?,?,?)".format(table)
		try:
			_debug("Helper: INSERTING {} for {}".format(len(query),table))
			cursor.executemany(queryMany,query)
		except sqlite3.OperationalError as e:
			if "locked" in e:
				time.sleep(0.1)
				cursor.executemany(queryMany,query)
		db.commit()
	db.close()
#def rebostPkgList_to_sqlite

def _rebostPkg_fill_data(rebostPkg,sanitize=True):
	if isinstance(rebostPkg['license'],list)==False:
		rebostPkg['license']=""
	categories=rebostPkg.get('categories',[])
	categories.extend(["","",""])
	name=rebostPkg.get('name','')
	if sanitize:
		name=rebostPkg.get('name','').strip().lower().replace('.','_')
		rebostPkg["name"]=name.strip()
		rebostPkg['pkgname']=rebostPkg['pkgname'].replace('.','_')
		rebostPkg['summary']=_sanitizeString(rebostPkg['summary'],scape=True)
		rebostPkg['description']=_sanitizeString(rebostPkg['description'],scape=True)
		if rebostPkg['icon'].startswith("http"):
			iconName=rebostPkg['icon'].split("/")[-1]
			iconPath=os.path.join("/usr/share/rebost-data/icons/cache/",iconName)
			if os.path.isfile(iconPath):
				rebostPkg['icon']=iconPath
		elif rebostPkg['icon']=='':
			iconName=rebostPkg['pkgname']
			iconPaths=[]
			iconPaths.append(os.path.join("/usr/share/rebost-data/icons/64x64/","{0}.png".format(iconName)))
			iconPaths.append(os.path.join("/usr/share/rebost-data/icons/64x64/","{0}_{0}.png".format(iconName)))
			iconPaths.append(os.path.join("/usr/share/rebost-data/icons/128x128/","{0}.png".format(iconName)))
			iconPaths.append(os.path.join("/usr/share/rebost-data/icons/128x128/","{0}_{0}.png".format(iconName)))
			while iconPaths:
				iconPath=iconPaths.pop(0)
				if os.path.isfile(iconPath):
					rebostPkg['icon']=iconPath
					break
		#fix LliureX category:
		lliurex=list(filter(lambda cat: 'lliurex' in str(cat).lower(), categories))
		if lliurex:
			idx=categories.index(lliurex.pop())
			if idx>0:
				categories.pop(idx)
				categories.insert(0,"Lliurex")
	(cat0,cat1,cat2)=categories[0:3]
	return([name,str(json.dumps(rebostPkg)),cat0,cat1,cat2])
#def _rebostPkg_fill_data

def _sanitizeString(data,scape=False,unescape=False):
	if isinstance(data,str):
		data=html2text.html2text(data)#,"lxml")
		data=data.replace("&","and")
		data=data.replace("`","")
		data=data.replace("´","")
		data=data.replace("\n"," ")
		data=data.replace("\\","*")
		data.rstrip()
		if scape:
			data=html.escape(data).encode('ascii', 'xmlcharrefreplace').decode() 
		if unescape:
			data=html.unescape(data)
	return(data)
#def _sanitizeString

def appstream_to_rebost(appstreamCatalogue):
	rebostPkgList=[]
	catalogue=appstreamCatalogue.get_apps()
	while catalogue:
		component=catalogue.pop(0)
		pkg=rebostPkg()
		pkg['id']=component.get_id().lower()
		pkg['name']=pkg['id'].split(".")[-1].lower().strip()
		if component.get_pkgname_default():
			pkg['pkgname']=component.get_pkgname_default()
		else:
			pkg['pkgname']=pkg['name']
		pkg['pkgname']=pkg['pkgname'].strip().replace("-desktop","")
		pkg['summary']=component.get_comment()
		pkg['summary']=_sanitizeString(pkg['summary'],scape=True)
		pkg['description']=component.get_description()
		if not isinstance(pkg['description'],str):
			pkg['description']=pkg['summary']
		else:
			pkg['description']=_sanitizeString(pkg['description'],scape=True)
		for icon in component.get_icons():
			fname=icon.get_filename()
			if fname:
				pkg['icon']=fname
				break
			url=icon.get_url()
			if url:
				if url.startswith("http"):
					pkg['icon']=url
					break

		pkg['categories']=component.get_categories()
		for i in component.get_bundles():
			if i.get_kind()==2: #appstream.BundleKind.FLATPAK:
				pkg['bundle']={'flatpak':component.get_id().replace('.desktop','')}
				versionArray=["0.0"]
				for release in component.get_releases():
					versionArray.append(release.get_version())
					versionArray.sort()
				pkg['versions']={'flatpak':versionArray[-1]}
		pkg['license']=component.get_project_license()
		for scr in component.get_screenshots():
			for img in scr.get_images():
				pkg['screenshots'].append(img.get_url())
				break
		homepage=''
		for kind in [appstream.UrlKind.UNKNOWN,appstream.UrlKind.HOMEPAGE,appstream.UrlKind.CONTACT,appstream.UrlKind.BUGTRACKER,appstream.UrlKind.HELP]:
			homepage=component.get_url_item(kind)
			if homepage:
				break
		pkg['homepage']=homepage

		rebostPkgList.append(pkg)
	return(rebostPkgList)
#def appstream_to_rebost

def generate_epi_for_rebostpkg(rebostpkg,bundle,user='',remote=False):
	if isinstance(rebostpkg,str):
		rebostpkg=json.loads(rebostpkg)
	#_debug("Generating EPI for:\n{}".format(rebostpkg))
	if os.path.isdir("/tmp/rebost")==False:
		os.makedirs("/tmp/rebost")
	tmpDir=tempfile.mkdtemp(dir="/tmp/rebost")
	os.chmod(tmpDir,0o755)
	if remote==False:
		_debug("Helper: Generate EPI for package {} bundle {}".format(rebostpkg.get('pkgname'),bundle))
		epijson=_generate_epi_json(rebostpkg,bundle,tmpDir=tmpDir)
	else:
		_debug("Helper: Generate REMOTE SCRIPT for package {} bundle {}".format(rebostpkg.get('pkgname'),bundle))
		epijson=''
		user=''
	if user=='root':
		user=''
	episcript=_generate_epi_sh(rebostpkg,bundle,user,remote,tmpDir=tmpDir)
	return(epijson,episcript)
#def generate_epi_for_rebostpkg
	
def _generate_epi_json(rebostpkg,bundle,tmpDir="/tmp"):
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
		epiFile["script"]={"name":"{0}_{1}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname')),bundle),'download':True,'remove':True,'getStatus':True,'getInfo':True}
		epiFile["custom_icon_path"]=iconFolder
		epiFile["required_root"]=True
		epiFile["check_zomando_state"]=False
		try:
			with open(epiJson,'w') as f:
				json.dump(epiFile,f,indent=4)
		except Exception as e:
			_debug("Helper {}".format(e))
			retCode=1
	return(epiJson)
#def _generate_epi_json

def _generate_epi_sh(rebostpkg,bundle,user='',remote=False,tmpDir="/tmp"):
	epiScript="{0}_{1}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname')),bundle)
	if not (os.path.isfile(epiScript) and remote==False):
		try:
			_make_epi_script(rebostpkg,epiScript,bundle,user,remote)
		except Exception as e:
			_debug("Helper: {}".format(e))
			print("ERROR {}".format(e))
			retCode=1
		if os.path.isfile(epiScript):
			os.chmod(epiScript,0o755)
	return(epiScript)
#def _generate_epi_sh

def _make_epi_script(rebostpkg,epiScript,bundle,user='',remote=False):
	_debug("Helper: Generating script for:\n{0} - {1} as user {2}".format(rebostpkg,bundle,user))
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

		if remote:
			f.write("function installPackage()\n{")
			f.write("\t\t{}\n".format(commands.get('installCmd')))
			for command in commands.get('installCmdLine',[]):
				f.write("\t\t{}\n".format(command))
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
		if remote==True:
			f.write("\ninstallPackage\n")

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
		installCmd="pkcon install -y {} 2>&1".format(rebostpkg['pkgname'])
		removeCmd="pkcon remove -y {} 2>&1".format(rebostpkg['pkgname'])
		removeCmdLine.append("TEST=$(pkcon resolve --filter installed {0}| grep {0} > /dev/null && echo 'installed')".format(rebostpkg['pkgname']))
		removeCmdLine.append("if [ \"$TEST\" == 'installed' ];then")
		removeCmdLine.append("exit 1")
		removeCmdLine.append("fi")
		statusTestLine=("TEST=$(pkcon resolve --filter installed {0}| grep {0} > /dev/null && echo 'installed')".format(rebostpkg['pkgname']))
	elif bundle=='snap':
		installCmd="snap install {} 2>&1".format(rebostpkg['bundle']['snap'])
		removeCmd="snap remove {} 2>&1".format(rebostpkg['bundle']['snap'])
		statusTestLine=("TEST=$( snap list 2> /dev/null| grep {} >/dev/null && echo 'installed')".format(rebostpkg['bundle']['snap']))
	elif bundle=='flatpak':
		installCmd="flatpak -y install {} 2>&1".format(rebostpkg['bundle']['flatpak'])
		removeCmd="flatpak -y uninstall {} 2>&1".format(rebostpkg['bundle']['flatpak'])
		statusTestLine=("TEST=$( flatpak list 2> /dev/null| grep $'{}\\t' >/dev/null && echo 'installed')".format(rebostpkg['bundle']['flatpak']))
	elif bundle=='appimage':
		#user=os.environ.get('USER')
		installCmd="wget -O /tmp/{}.appimage {} 2>&1".format(rebostpkg['pkgname'],rebostpkg['bundle']['appimage'])
		destdir="/opt/appimages"
		if user!='root' and user:
			destdir=os.path.join("/home",user,".local","bin")
		installCmdLine.append("mkdir -p {}".format(destdir))
		installCmdLine.append("mv /tmp/{0}.appimage {1}".format(rebostpkg['pkgname'],destdir))
		destPath=os.path.join(destdir,"{}.appimage".format(rebostpkg['pkgname']))
		installCmdLine.append("chmod +x {}".format(destPath))
		if user!='root' and user:
			installCmdLine.append("chown {0}:{0} {1}".format(user,destPath))
			installCmdLine.append("[ -e /home/{1}/Appimages ] || ln -s {0} /home/{1}/Appimages".format(destdir,user))
			installCmdLine.append("[ -e /home/{0}/Appimages ] && chown -R {0}:{0} /home/{0}/Appimages".format(user))
			installCmdLine.append("/usr/share/app2menu/app2menu-helper.py {0} {1} \"{2}\" \"{3}\" \"{4}\" /home/{5}/.local/share/applications/{0} {4}".format(rebostpkg['pkgname'],rebostpkg['icon'],rebostpkg['summary'],";".join(rebostpkg['categories']),destPath,user))
		statusTestLine=("TEST=$( ls {}  1>/dev/null 2>&1 && echo 'installed')".format(destPath))
		removeCmd="rm {0} && rm /home/{1}/.local/share/applications/{2}.desktop".format(destPath,user,rebostpkg['pkgname'])
		statusTestLine=("TEST=$( ls {}  1>/dev/null 2>&1 && echo 'installed')".format(destPath))
	elif bundle=='zomando':
		installCmd="{}".format(os.path.join("exec/usr/share/zero-center/zmds/",rebostpkg['bundle']['zomando']))
		removeCmd="{}".format(os.path.join("exec /usr/share/zero-center/zmds/",rebostpkg['bundle']['zomando']))
		statusTestLine=("TEST=$([ -e /usr/share/zero-center/zmds/%s ] && [[ ! -n $(grep epi /usr/share/zero-center/zmds/%s) ]] && echo installed || n4d-vars getvalues ZEROCENTER | tr \",\" \"\\n\"|awk -F ',' 'BEGIN{a=0}{if ($1~\"%s\"){a=1};if (a==1){if ($1~\"state\"){ b=split($1,c,\": \");if (c[b]==1) print \"installed\";a=0}}}')"%(rebostpkg['bundle']['zomando'],rebostpkg['bundle']['zomando'],rebostpkg['bundle']['zomando'].replace(".zmd","")))

	commands['installCmd']=installCmd
	commands['installCmdLine']=installCmdLine
	commands['removeCmd']=removeCmd
	commands['removeCmdLine']=removeCmdLine
	commands['statusTestLine']=statusTestLine
	return(commands)
#def _get_bundle_commands

def get_epi_status(episcript):
	st="0"
	if os.path.exists(episcript)==True:
		try:
			proc=subprocess.run([episcript,'getStatus'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			st=proc.stdout.decode().strip()
		except Exception as e:
			_debug(e)
	return(st)
#def get_epi_status

def get_table_state(pkg,bundle):
	tablePath="/usr/share/rebost/installed.db"
	ret=[]
	if os.path.isfile(tablePath):
		db=sqlite3.connect(tablePath)
		cursor=db.cursor()
		query="Select * from installed where pkg='{0}' and bundle='{1}'".format(pkg,bundle)
		cursor.execute(query)
		ret=cursor.fetchall()
		db.close()
	return ret
#def get_table_state

def check_remove_unsure(package):
	sw=False
	_debug("Helper: Checking if remove {} is unsure".format(package))
	proc=subprocess.run(["apt-cache","rdepends",package],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	try:
		llx=subprocess.run(["lliurex-version","-f"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		version=llx.stdout.decode().strip()
	except:
		version="desktop"
	for depend in proc.stdout.decode().split("\n"):
		if "lliurex-meta-{}".format(version) in depend:
			sw=True
			break
	_debug("Helper: {}".format(proc.stdout))
	_debug("Helper: Checked")
	return(sw)
#def check_remove_unsure(package):
