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
	pkg={'name':'','id':'','size':'','screenshots':[],'video':[],'pkgname':'','description':'','summary':'','icon':'','size':{},'downloadSize':'','bundle':{},'kind':'','version':'','versions':{},'installed':'','banner':'','license':'','homepage':'','categories':[],'installerUrl':'','state':{}}
	return(pkg)

def rebostPkgList_to_sqlite(rebostPkgList,table,drop=True):
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
		_debug(query)
		cursor.execute(query)
	query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT,cat0 TEXT, cat1 TEXT, cat2 TEXT);".format(table)
	_debug(query)
	cursor.execute(query)
	query=[]
	for rebostPkg in rebostPkgList:
		name=rebostPkg.get('pkgname','').strip().lower().replace('.','_')
		rebostPkg["name"]=rebostPkg.get('name','').strip()
		rebostPkg['pkgname']=rebostPkg['pkgname'].replace('.','_')
		rebostPkg['summary']=_sanitizeString(rebostPkg['summary'],scape=True)
		rebostPkg['description']=_sanitizeString(rebostPkg['description'],scape=True)
		if isinstance(rebostPkg['license'],list)==False:
			rebostPkg['license']=""
		if rebostPkg['icon'].startswith("http"):
			iconName=rebostPkg['icon'].split("/")[-1]
			iconPath=os.path.join("/usr/share/rebost-data/icons/cache/",iconName)
			if os.path.isfile(iconPath):
				rebostPkg['icon']=iconPath
		elif rebostPkg['icon']=='':
			iconName=rebostPkg['pkgname']
			iconPath=os.path.join("/usr/share/rebost-data/icons/64x64/","{0}.png".format(iconName))
			iconPath2=os.path.join("/usr/share/rebost-data/icons/64x64/","{0}_{0}.png".format(iconName))
			iconPath128=os.path.join("/usr/share/rebost-data/icons/128x128/","{0}.png".format(iconName))
			iconPath2128=os.path.join("/usr/share/rebost-data/icons/128x128/","{0}_{0}.png".format(iconName))
			if os.path.isfile(iconPath):
				rebostPkg['icon']=iconPath
			elif os.path.isfile(iconPath2):
				rebostPkg['icon']=iconPath2
			elif os.path.isfile(iconPath128):
				rebostPkg['icon']=iconPath128
			elif os.path.isfile(iconPath2128):
				rebostPkg['icon']=iconPath2128
		#fix LliureX category:
		categories=rebostPkg.get('categories',[])
		if ('LliureX' in categories) or ('Lliurex' in categories) or ("lliurex" in categories):
			try:
				idx=categories.index("LliureX")
			except:
				try:
					idx=categories.index("lliurex")
				except:
					idx=categories.index("Lliurex")
			if idx>0:
				categories.pop(idx)
				categories.insert(0,"Lliurex")
		while len(categories)<3:
			categories.append(None)
		(cat0,cat1,cat2)=categories[0:3]
		if name=="firefox":
			print(rebostPkg)
		query.append([name,str(json.dumps(rebostPkg)),cat0,cat1,cat2])
	
	if query:
		queryMany="INSERT or REPLACE INTO {} VALUES (?,?,?,?,?)".format(table)
		try:
			_debug("INSERTING {} for {}".format(len(query),table))
			cursor.executemany(queryMany,query)
		except Exception as e:
			_debug(e)
#			_debug(query)
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
	name=rebostPkg.get('pkgname','').strip().lower().replace('.','_')
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
		data=data.replace("`","")
		data=data.replace("´","")
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
				pkg['pkgname']=('-').join(candidateName)
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
				pkg['versions']={'flatpak':versionArray[-1]}
		pkg['license']=component.get_project_license()
		for scr in component.get_screenshots():
			for img in scr.get_images():
				pkg['screenshots'].append(img.get_url())
				break

		rebostPkgList.append(pkg)
	return(rebostPkgList)
#def appstream_to_rebost

def generate_epi_for_rebostpkg(rebostpkg,bundle,user='',remote=False):
	if isinstance(rebostpkg,str):
		rebostpkg=json.loads(rebostpkg)
	#_debug("Generating EPI for:\n{}".format(rebostpkg))
	tmpDir=tempfile.mkdtemp()
	os.chmod(tmpDir,0o755)
	if remote==False:
		_debug("Generate EPI for package {} bundle {}".format(rebostpkg.get('pkgname'),bundle))
		epijson=_generate_epi_json(rebostpkg,bundle,tmpDir=tmpDir)
	else:
		_debug("Generate REMOTE SCRIPT for package {} bundle {}".format(rebostpkg.get('pkgname'),bundle))
		epijson=''
		user=''
	if user=='root':
		user=''
	episcript=_generate_epi_sh(rebostpkg,bundle,user,remote,tmpDir=tmpDir)
	return(epijson,episcript)
	
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

def _generate_epi_sh(rebostpkg,bundle,user='',remote=False,tmpDir="/tmp"):
	epiScript="{}_{}_script.sh".format(os.path.join(tmpDir,rebostpkg.get('pkgname')),bundle)
	if not (os.path.isfile(epiScript) and remote==False):
		try:
			_make_epi_script(rebostpkg,epiScript,bundle,user,remote)
		except Exception as e:
			_debug("%s"%e)
			retCode=1
		if os.path.isfile(epiScript):
			os.chmod(epiScript,0o755)
	return(epiScript)
#def _generate_epi_sh

def _make_epi_script(rebostpkg,epiScript,bundle,user='',remote=False):
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
		destdir="/opt/appimages"
		if user:
			destdir=os.path.join("/home",user,".local/bin")
		installCmdLine.append("mkdir -p {}".format(destdir))
		installCmdLine.append("mv /tmp/{0}.appimage {1}".format(rebostpkg['pkgname'],destdir))
		destPath=os.path.join(destdir,"{}.appimage".format(rebostpkg['pkgname']))
		installCmdLine.append("chmod +x {}".format(destPath))
		if user:
			installCmdLine.append("chown {0}:{0} {1}".format(user,destPath))
			installCmdLine.append("[ -e /home/{1}/Appimages ] || ln -s {0} /home/{1}/Appimages".format(destdir,user))
			installCmdLine.append("[ -e /home/{0}/Appimages ] && chown -R {0}:{0} /home/{0}/Appimages".format(user))
		statusTestLine=("TEST=$( ls {}  1>/dev/null 2>&1 && echo 'installed')".format(destPath))
		removeCmd="rm {}".format(destPath)
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

def get_epi_status(episcript):
	st=""
	if os.path.exists(episcript)==True:
		try:
			proc=subprocess.run([episcript,'getStatus'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			st=proc.stdout.decode().strip()
		except Exception as e:
			_debug(e)
	return(st)

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
