#!/usr/bin/env python3
import os,shutil,distro,stat
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
import flatpakHelper

DBG=False
dbCache="/tmp/.cache/rebost"
WRKDIR=os.path.join(dbCache,os.environ.get("USER"))
if os.path.exists(WRKDIR)==False:
	os.makedirs(WRKDIR)
os.chmod(WRKDIR,stat.S_IRWXU )
path=os.path.join(WRKDIR,"rebost.log")
if os.path.isdir(os.path.dirname(path))==False:
	os.makedirs(os.path.dirname(path))
f=open(path,"w")
f.close()
fname = "rebost.log"
logger = logging.getLogger(fname)
formatter = logging.Formatter('%(asctime)s %(message)s')
fh=logging.FileHandler(path)
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)
st=logging.StreamHandler()
st.setLevel(logging.DEBUG)
st.setFormatter(formatter)
#logger.addHandler(st)

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

def rebostPkgList_to_sqlite(rebostPkgList,table,drop=False,sanitize=True):
	wrkDir=WRKDIR #"/usr/share/rebost"
	tablePath=os.path.join(wrkDir,os.path.basename(table))
	if drop:
		if os.path.isfile(tablePath):
			os.remove(tablePath)
	db=sqlite3.connect(tablePath)
	table=table.replace('.db','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT,cat0 TEXT, cat1 TEXT, cat2 TEXT, alias TEXT);".format(table)
	_debug("Helper: {}".format(query))
	cursor.execute(query)
	query=[]
	while rebostPkgList:
		rebostPkg=rebostPkgList.pop(0)
		values=[]
		values=(_rebostPkg_fill_data(rebostPkg,sanitize))
		pkgName=values[0]
		pkgData=values[1]
		queryTmp='SELECT data FROM {0} where pkg="{1}"'.format(table,pkgName)
		cursor.execute(queryTmp)
		row=cursor.fetchone()
		if row!=None:
			if len(row)>0:
				if pkgData!=row[0]:
					query.append(values)
				#else:
				#	_debug("Already inserted {}".format(pkgName))
			else:
				query.append(values)
		else:
			query.append(values)
		#take breath
		#if len(rebostPkgList)%20==0:
		#	time.sleep(0.001)
	if query:
		queryMany="INSERT or REPLACE INTO {} VALUES (?,?,?,?,?,?)".format(table)
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
	wrkDir=WRKDIR #"/usr/share/rebost"
	tablePath=os.path.join(wrkDir,os.path.basename(table))
	if tablePath.endswith(".db")==False:
		tablePath+=".db"
	db=sqlite3.connect(tablePath)
	table=table.replace('.db','')
	cursor=db.cursor()
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT,cat0 TEXT,cat1 TEXT, cat2 TEXT);".format(table)
	cursor.execute(query)
	query=_rebostPkg_fill_data(rebostPkg)
	if query:
		queryMany="INSERT or REPLACE INTO {} VALUES (\'{}\',\'{}\',\'{}\',\'{}\',\'{}\',\'{}\')".format(table,query[0],query[1],query[2],query[3],query[4],query[5])
		try:
			_debug("Helper: INSERT package for {}".format(table))
			cursor.execute(queryMany)
		except sqlite3.OperationalError as e:
			time.sleep(0.1)
			cursor.execute(queryMany)
		try:
			db.commit()
		except sqlite3.OperationalError as e:
			time.sleep(0.1)
			db.commit()
	db.close()
	cursor=None
#def rebostPkgList_to_sqlite

def _rebostPkg_fill_data(rebostPkg,sanitize=True):
	if isinstance(rebostPkg['license'],list)==False:
		rebostPkg['license']=""
	alias=""
	name=rebostPkg.get('name','')
	if sanitize:
		name=rebostPkg.get('name','').strip().lower()
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
			iconPaths.append(os.path.join("/usr/share/icons/lliurex/apps/48/{0}.png".format(iconName)))
			while iconPaths:
				iconPath=iconPaths.pop(0)
				if os.path.isfile(iconPath):
					rebostPkg['icon']=iconPath
					break
		elif "/flatpak/" in rebostPkg["icon"] and os.path.isfile(rebostPkg["icon"])==False:
			rebostPkg["icon"]=self._fixFlatpakIconPath(rebostPkg['icon'])
		for bun in rebostPkg["bundle"].keys():
			rebostPkg["bundle"][bun]=str(rebostPkg["bundle"][bun])
			
	#fix LliureX categories:
	cats=rebostPkg.get('categories',[])
	categories=[ c.lower() for c in cats if c ]
	while len(categories)<3:
		categories.append("")
	for c in ["zomando","lliurex"]:
		if c in categories:
			categories.remove(c)
			categories.insert(0,c)
	categories=[ c.capitalize() for c in categories ]
	#	llxcat=list(filter(lambda cat: c in str(cat).lower(), categories))
	#	if llxcat:
	#		idx=categories.index(llxcat.pop())
	#		if idx>0:
	#			categories.pop(idx)
	#			categories.insert(0,c.capitalize())
	(cat0,cat1,cat2)=categories[0:3]
	alias=rebostPkg.get("alias","")
	return([name,str(json.dumps(rebostPkg)),cat0,cat1,cat2,alias])
#def _rebostPkg_fill_data

def _fixFlatpakIconPath(self,icon):
	fpath=os.path.dirname(icon)
	spath=fpath.split("/")
	idx=0
	if "icons" in spath:
		idx=spath.index("icons")-1
		fpath="/".join(spath[0:idx])
	if os.path.isdir(fpath) and idx>0:
		for d in os.listdir(fpath):
			if os.path.isdir(os.path.join(fpath,d,"icons")):
				icon=os.path.join(fpath,d,"/".join(spath[idx+1:]),os.path.basename(rebostPkg['icon']))
	return icon
#def _fixFlatpakIconPath

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
		if unescape:
			data=html.unescape(data)
	return(data)
#def _sanitizeString

def rebostToAppstream(rebostPkgList,fname=""):
	if len(fname)==0:
		fname="/usr/share/rebost-data/yaml/lliurex_dists_focal_main_dep11_Components-amd64.yml"
	store=appstream.Metadata()
	for rebostPkg in rebostPkgList:
		app=appstream.Component()
		app.set_id(rebostPkg["id"])
		app.set_name(rebostPkg["name"])
		app.set_description(rebostPkg["description"],None)
		app.set_summary(rebostPkg["summary"],None)
		app.set_pkgname(rebostPkg["pkgname"])
		app.set_kind(appstream.ComponentKind.GENERIC)
		icon=appstream.Icon()
		if "://" in rebostPkg["icon"]:
			icon.set_url(rebostPkg["icon"])
			icon.set_kind(appstream.IconKind.REMOTE)
		else:
			icon.set_filename(rebostPkg["icon"])
			icon.set_kind(appstream.IconKind.CACHED)
		app.add_icon(icon)
		screenshot=appstream.Screenshot()
		#for img in rebostPkg["screenshots"]
			#screenshot.dd
		store.add_component(app)
	xml=store.components_to_catalog(appstream.FormatKind.YAML)
	with open(fname,"w") as f:
		f.write(xml)
	return(fname)
#def rebostToAppstream

def appstream_to_rebost(appstreamCatalogue):
	rebostPkgList=[]
	catalogue=appstreamCatalogue.get_apps()
	while catalogue:
		component=catalogue.pop(0)
		pkg=rebostPkg()
		pkg['id']=component.get_id().lower()
		pkg['name']=_componentGetName(component)
		if component.get_pkgname_default():
			pkg['pkgname']=component.get_pkgname_default()
		else:
			pkg['pkgname']=pkg['name']
		pkg['pkgname']=pkg['pkgname'].strip().replace("-desktop","")
		pkg['summary']=_sanitizeString(component.get_comment(),scape=True)
		pkg['description']=component.get_description()
		if not isinstance(pkg['description'],str):
			pkg['description']=pkg['summary']
		else:
			pkg['description']=_sanitizeString(pkg['description'],scape=True)
		pkg['icon']=_componentGetIcon(component)
		if "/flatpak/" in pkg["icon"] and os.path.isfile(pkg["icon"])==False:
			pkg["icon"]=self._fixFlatpakIconPath(pkg['icon'])
		pkg['homepage']=_componentGetHomepage(component)
		pkg['categories']=component.get_categories()
		pkg=_componentFillInfo(component,pkg)
		pkg['license']=component.get_project_license()
		pkg['screenshots']=_componentGetScreenshots(component)
		rebostPkgList.append(pkg)
	return(rebostPkgList)
#def appstream_to_rebost

def _componentGetName(component):
	name=component.get_id()
	nameComponents=name.lower().split(".")
	cont=len(nameComponents)-1
	banlist=["desktop","org","net","com"]
	name=nameComponents[-1].lower()
	while cont>=0:
		if nameComponents[cont].lower() not in banlist:
			name=nameComponents[cont].lower()
			break
		cont-=1
	name=name.replace("_zmd",'')
	return(name)
#def _componentGetName

def _componentGetIcon(component):
	iconf=""
	for icon in component.get_icons():
		if icon.get_filename():
			iconf=icon.get_filename()
			break
		url=icon.get_url()
		if url:
			if url.startswith("http"):
				iconf=url
				break
	return(iconf)
#def _componentGetIcon

def _componentGetHomepage(component):
		homepage=''
		for kind in [appstream.UrlKind.UNKNOWN,appstream.UrlKind.HOMEPAGE,appstream.UrlKind.CONTACT,appstream.UrlKind.BUGTRACKER,appstream.UrlKind.HELP]:
			homepage=component.get_url_item(kind)
			if homepage:
				break
		return(homepage)
#def _componentGetHomepage

def _componentFillInfo(component,pkg):
	versionArray=[]
	for release in component.get_releases():
		versionArray.append(release.get_version())
	if len(versionArray)==0:
		versionArray=["0.9~{}".format(distro.codename())]
	versionArray.sort()
	if len(component.get_bundles())>0:
		for i in component.get_bundles():
			if i.get_kind()==2 or i.get_kind()==4: #appstream.BundleKind.FLATPAK | PACKAGE:
				if i.get_kind()==2:
					bundle="flatpak"
					pkgid=component.get_id()
				else:
					pkgid=component.get_pkgname_default()
					bundle="package"
				pkg['bundle']={bundle:pkgid.replace('.desktop','')}
				pkg['versions']={bundle:versionArray[-1]}
			if i.get_kind()==1: #appstream.BundleKind.LIMBA
					pkgid=component.get_id()
					pkg['bundle']={"eduapp":pkgid.replace('.desktop','')}
		if "lliurex"  in component.get_id():
			pkg=_componentLliurexPackage(component,pkg)
		elif "Lliurex" in pkg['categories'] or "LliureX" in pkg['categories']:
				pkg['bundle']={'package':pkg['pkgname']}
				pkg['homepage']="https://github.com/lliurex"
	return(pkg)
#def _componentFillInfo

def _componentLliurexPackage(component,pkg):
	pkgName=component.get_id().replace('.desktop','')
	pkgName=pkgName.replace('_zmd','')
	zmdPkgName=pkgName
	if zmdPkgName.endswith(".zmd")==False and "Zomando" in pkg['categories']:
		zmdPkgName="{}.zmd".format(zmdPkgName)
	if "Zomando" in pkg['categories'] and "Software" in pkg['categories']:
		pkg['bundle']={'package':pkgName,'zomando':zmdPkgName}
	elif "Education" in pkg['categories'] or "Utility" in pkg['categories']:
		if "Zomando" in pkg['categories']:
			pkg['bundle']={'package':pkg['pkgname'],'zomando':zmdPkgName}
		else:
			pkg['bundle']={'package':pkg['pkgname']}
	if not("Lliurex" in pkg['categories']) and not("LliureX" in pkg['categories']):
		pkg['categories'].insert(0,"Lliurex")
	pkg['homepage']="https://github.com/lliurex"
	return(pkg)
#def _componentLliurexPackage

def _componentGetScreenshots(component):
	screenshots=[]
	for scr in component.get_screenshots():
		for img in scr.get_images():
			screenshots.append(img.get_url())
			break
		if len(screenshots)>3:
			break
	return(screenshots)
#def _componentGetScreenshots

def generate_epi_for_rebostpkg(rebostpkg,bundle,user='',remote=False):
	if isinstance(rebostpkg,str):
		rebostpkg=json.loads(rebostpkg)
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
#		try:
		_make_epi_script(rebostpkg,epiScript,bundle,user,remote)
#		except Exception as e:
#			_debug("Helper: {}".format(e))
#			print("Generate_epi error {}".format(e))
#			retCode=1
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
		f.write("ERR=0\n")
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
		f.write("\t\techo \"{}\"\n".format(_sanitizeString(rebostpkg['description'],scape=True)))
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

		f.write("exit $ERR\n")
#def _make_epi_script

def _get_bundle_commands(bundle,rebostpkg,user=''):
	commands={}
	installCmd=''
	installCmdLine= []
	removeCmd=''
	removeCmdLine=[]
	statusTestLine=''
	if bundle=='package':
		(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=_get_package_commands(rebostpkg,user)
	elif bundle=='snap':
		(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=_get_snap_commands(rebostpkg,user)
	elif bundle=='flatpak':
		(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=_get_flatpak_commands(rebostpkg,user)
	elif bundle=='appimage':
		(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=_get_appimage_commands(rebostpkg,user)
	elif bundle=='zomando':
		(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=_get_zomando_commands(rebostpkg,user)
	commands['installCmd']=installCmd
	commands['installCmdLine']=installCmdLine
	commands['removeCmd']=removeCmd
	commands['removeCmdLine']=removeCmdLine
	commands['statusTestLine']=statusTestLine
	return(commands)
#def _get_bundle_commands

def _get_package_commands(rebostpkg,user):
	(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=("",[],"",[],"")
	#installCmd="pkcon install --allow-untrusted -y {} 2>&1;ERR=$?".format(rebostpkg['pkgname'])
	#pkcon has a bug detecting network if there's no network under NM (fails with systemd-networkd)
	#Temporary use apt until bug fix

	installCmd="export DEBIAN_FRONTEND=noninteractive"
	installCmdLine.append("export DEBIAN_PRIORITY=critical")
	installCmdLine.append("apt-get -qy -o \"Dpkg::Options::=--force-confdef\" -o \"Dpkg::Options::=--force-confold\" install {} 2>&1;ERR=$?".format(rebostpkg['pkgname']))
	#removeCmd="pkcon remove -y {} 2>&1;ERR=$?".format(rebostpkg['pkgname'])
	removeCmd="apt remove -y {} 2>&1;ERR=$?".format(rebostpkg['pkgname'])
	removeCmdLine.append("TEST=$(pkcon resolve --filter installed {0}| grep {0} > /dev/null && echo 'installed')".format(rebostpkg['pkgname']))
	removeCmdLine.append("if [ \"$TEST\" == 'installed' ];then")
	removeCmdLine.append("exit 1")
	removeCmdLine.append("fi")
	statusTestLine=("TEST=$(pkcon resolve --filter installed {0}| grep {0} > /dev/null && echo 'installed')".format(rebostpkg['pkgname']))
	return(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)
#def _get_package_commands

def _get_snap_commands(rebostpkg,user):
	(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=("",[],"",[],"")
	installCmd="snap install {} 2>&1;ERR=$?".format(rebostpkg['bundle']['snap'])
	removeCmd="snap remove {} 2>&1;ERR=$?".format(rebostpkg['bundle']['snap'])
	statusTestLine=("TEST=$( snap list 2> /dev/null| grep {} >/dev/null && echo 'installed')".format(rebostpkg['bundle']['snap']))
	return(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)
#def _get_snap_commands

def _get_flatpak_commands(rebostpkg,user):
	(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=("",[],"",[],"")
	installCmd="flatpak -y install {} 2>&1;ERR=$?".format(rebostpkg['bundle']['flatpak'])
	removeCmd="flatpak -y uninstall {} 2>&1;ERR=$?".format(rebostpkg['bundle']['flatpak'])
	statusTestLine=("TEST=$( flatpak list 2> /dev/null| grep $'{}\\t' >/dev/null && echo 'installed')".format(rebostpkg['bundle']['flatpak']))
	return(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)
#def _get_flatpak_commands

def _get_appimage_commands(rebostpkg,user):
	(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=("",[],"",[],"")
	#user=os.environ.get('USER')
	installCmd=""
	installCmd="wget -O /tmp/{}.appimage {} 2>&1;ERR=$?".format(rebostpkg['pkgname'],rebostpkg['bundle']['appimage'])
	destdir="/opt/appimages"
	if user!='root' and user:
		destdir=os.path.join("/home",user,".local","bin")
	installCmdLine.append("mkdir -p {}".format(destdir))
	installCmdLine.append("mv /tmp/{0}.appimage {1}".format(rebostpkg['pkgname'],destdir))
	destPath=os.path.join(destdir,"{}.appimage".format(rebostpkg['pkgname']))
	deskName="{}-appimage.desktop".format(rebostpkg['pkgname'])
	installCmdLine.append("chmod +x {}".format(destPath))
	if user!='root' and user:
		installCmdLine.append("chown {0}:{0} {1}".format(user,destPath))
		installCmdLine.append("[ -e /home/{1}/Appimages ] || ln -s {0} /home/{1}/Appimages".format(destdir,user))
		installCmdLine.append("[ -e /home/{0}/Appimages ] && chown -R {0}:{0} /home/{0}/Appimages".format(user))
		installCmdLine.append("/usr/share/app2menu/app2menu-helper.py {0} \"{1}\" \"{2}\" \"{3}\" \"{4}\" /home/{5}/.local/share/applications/{6} {4}".format(rebostpkg['pkgname'],rebostpkg['icon'],rebostpkg['summary'],";".join(rebostpkg['categories']),destPath,user,deskName))
		installCmdLine.append("chown {0}:{0} /home/{0}/.local/share/applications/{1}".format(user,deskName))
	removeCmd="rm {0} && rm /home/{1}/.local/share/applications/{2}-appimage.desktop;ERR=$?".format(destPath,user,rebostpkg['pkgname'])
	statusTestLine=("TEST=$( ls {}  1>/dev/null 2>&1 && echo 'installed')".format(destPath))
	return(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)
#def _get_appimage_commands

def _get_zomando_commands(rebostpkg,user):
	(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)=("",[],"",[],"")
	installCmd="{}".format(os.path.join("exec /usr/share/zero-center/zmds/",rebostpkg['bundle']['zomando']))
	removeCmd="{}".format(os.path.join("exec /usr/share/zero-center/zmds/",rebostpkg['bundle']['zomando']))
	#statusTestLine=("TEST=$([ -e /usr/share/zero-center/zmds/%s ] && [[ ! -n $(grep epi /usr/share/zero-center/zmds/%s) ]] && echo installed || n4d-vars getvalues ZEROCENTER | tr \",\" \"\\n\"|awk -F ',' 'BEGIN{a=0}{if ($1~\"%s\"){a=1};if (a==1){if ($1~\"state\"){ b=split($1,c,\": \");if (c[b]==1) print \"installed\";a=0}}}')"%(rebostpkg['bundle']['zomando'],rebostpkg['bundle']['zomando'],rebostpkg['bundle']['zomando'].replace(".zmd","")))
	statusTestLine=("TEST=$([ -e /usr/share/zero-center/zmds/%s ]  && echo installed || n4d-vars getvalues ZEROCENTER | tr \",\" \"\\n\"|awk -F ',' 'BEGIN{a=0}{if ($1~\"%s\"){a=1};if (a==1){if ($1~\"state\"){ b=split($1,c,\": \");if (c[b]==1) print \"installed\";a=0}}}')"%(rebostpkg['bundle']['zomando'],rebostpkg['bundle']['zomando'].replace(".zmd","")))
	return(installCmd,installCmdLine,removeCmd,removeCmdLine,statusTestLine)
#def _get_zomando_commands

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

def get_table_pkg(table,pkg):
	#tablePath=os.path.join("/usr/share/rebost/",table)
	tablePath=os.path.join(WRKDIR,table)
	ret=[]
	if os.path.isfile(tablePath):
		tableName=table.replace(".db","").lower()
		db=sqlite3.connect(tablePath)
		cursor=db.cursor()
		query="Select * from {0} where pkg='{1}'".format(tableName,pkg)
		try:
			cursor.execute(query)
			ret=cursor.fetchall()
		except:
			pass
		db.close()
	return ret
#def get_table_state

def get_table_pkgarray(table,pkgarray):
	tablePath=os.path.join(WRKDIR,table)
	ret=[]
	if os.path.isfile(tablePath):
		tableName=table.replace(".db","").lower()
		db=sqlite3.connect(tablePath)
		cursor=db.cursor()
		query="Select * from {0} where pkg in ({1})'".format(tableName,",".join(pkgarray))
		try:
			cursor.execute(query)
			ret=cursor.fetchall()
		except:
			pass
		db.close()
	return ret
#def get_table_pkgarray

def get_table_state(pkg,bundle):
	tablePath=os.path.join(WRKDIR,"installed.db")
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

def getFiltersList(banlist=False,includelist=False,wordlist=False):
	wrkDir=WRKDIR #"/usr/share/rebost"
	folderbanlist=os.path.join(wrkDir,"lists.d/banned")
	folderincludelist=os.path.join(wrkDir,"lists.d/include")
	folderWordlist=os.path.join(wrkDir,"lists.d/words")
	files={"categories":[],"apps":[]}
	filters={"banlist":files,"includelist":files,"words":[]}
	if banlist==True:
		filters["banlist"]=getFilterContent(folderbanlist)
	if includelist==True:
		filters["includelist"]=getFilterContent(folderincludelist)
	if wordlist==True:
		filters["words"]=getFilterContent(folderWordlist)
	return(filters)

def getFilterContent(folder):
	filters={"categories":[],"apps":[]}
	if "word" in folder:
		folders=[folder]
		filters=[]
	else:
		folders=[os.path.join(folder,"categories"),os.path.join(folder,"apps")]
	for folder in folders:
		if os.path.isdir(folder):
			for f in os.listdir(folder):
				if f.endswith("conf"):
					with open(os.path.join(folder,f),"r") as ffilter:
						for line in ffilter.readlines():
							fcontent=line.strip()
							if "categories" in folder:
								filters["categories"].append(fcontent)
							elif "apps" in folder:
								filters["apps"].append(fcontent)
							else:
								filters.append(fcontent)
	return(filters)
	#Default banlist. If there's a category banlist file use it

#	banlist=["ActionGame", "Actiongame", "Adventure", "AdventureGame", "Adventuregame", "Amusement","ArcadeGame", "Arcadegame", "BlocksGame", "Blocksgame", "BoardGame", "Boardgame", "Building", "CardGame", "Cardgame", "Chat", "Communication", "Communication & News", "Communication & news",  "ConsoleOnly", "Consoleonly", "Construction", "ContactManagement", "Contactmanagement", "Email", "Emulation", "Emulator",  "Fantasy", "Feed", "Feeds",  "Game", "Games",  "IRCClient",  "InstantMessaging", "Instantmessaging",  "Ircclient",  "LogicGame", "Logicgame", "MMORPG",  "Matrix",  "Mmorpg",  "News", "P2P", "P2p", "PackageManager", "Packagemanager", "Player", "Players", "RemoteAccess", "Remoteaccess",  "Role Playing", "Role playing", "RolePlaying", "Roleplaying",  "Services", "Settings", "Shooter", "Simulation",  "SportsGame", "Sportsgame", "Strategy", "StrategyGame", "Strategygame", "System", "TV", "Telephony", "TelephonyTools", "Telephonytools", "TerminalEmulator", "Terminalemulator",  "Tuner", "Tv", "Unknown", "VideoConference", "Videoconference","WebBrowser"]
		#appsbanlist=["cryptochecker","digibyte-core","grin","hyperdex","vertcoin-core","syscoin-core","ryowallet","radix_wallet","obsr","nanowallet","mycrypto","p2pool","zapdesktop","demonizer"]
		#includelist=['graphics', 'Chart', 'Clock', 'Astronomy', 'AudioVideo', 'Publishing', 'Presentation', 'Biology', 'NumericalAnalysis', 'Viewer', 'DataVisualization','Development', 'TextTools', 'FlowChart',  'FP', 'Music', 'Physics', 'Lliurex', 'Scanning', 'Photography', 'resources', 'Productivity',  'MedicalSoftware', 'Graphics', 'Literature', 'Science', 'Zomando',  'Support', 'Geology',  'Engineering', 'Spirituality', '3DGraphics',  'Humanities',  'electronics', 'fonts',  '2DGraphics', 'Math', 'Electricity', 'GUIDesigner', 'Sequencer', 'Chemistry', 'publishing',  'Recorder', 'X-CSuite', 'Accessibility',  'DiscBurning',  'IDE', 'LearnToCode', 'TextEditor', 'Animation', 'Maps', 'Documentation', 'documentation', 'Dictionary', 'Spreadsheet', 'Office', 'Education', 'Art', 'KidsGame', 'Finance', 'Database', 'ComputerScience', 'Sports','WebDevelopment', 'VectorGraphics', 'Debugger', 'Midi',  'OCR', 'Geography',  'Electronics',  'Languages', 'education', 'RasterGraphics', 'Calculator', 'science', 'Translation', 'ImageProcessing', 'Economy', 'Geoscience', 'HamRadio', 'Webdevelopment', 'AudioVideoEditing',  'WordProcessor']
#def getCategoriesbanlist
