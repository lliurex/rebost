#!/usr/bin/env python3
import os,distro,stat,copy
import json
import tempfile
import rebostHelper
import logging
import locale
import hashlib
import n4d.client as n4d
import subprocess
from epi import epimanager

EPIC="/usr/sbin/epic"

class epicHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.packagekind="zomando"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=1
		self.store=None
		self.epiManager=epimanager.EpiManager()
		self.user=''
		if kwargs:
			self.user=kwargs.get('user','')
		self.zmdDir="/usr/share/zero-center/zmds"
		self.appDir="/usr/share/zero-center/applications"
		self.appDirFiles=[]
		if os.path.isdir(self.appDir):
			self.appDirFiles=os.listdir(self.appDir)
		self.iconDir="/usr/share/banners/lliurex-neu/"
		self.locales=[locale.getdefaultlocale()[0].split("_")[0]]
		self.locales.append("qcv")
		if self.locales[0]=="ca":
			self.locales.append("es")
		else:
			self.locales.append("ca")
		self.locales.append("en")
		cmd=["/usr/bin/lliurex-version","-n"]
		try:
			out=subprocess.check_output(cmd,encoding="utf8",universal_newlines=True)
		except Exception as e:
			print(e)
			out=distro.codename()
		self.release=out.strip()
		self.n4d=n4d.Client()
		dbCache="/tmp/.cache/rebost"
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER",""))
		if os.path.exists(self.rebostCache)==False:
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","ep.lu")
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="epicHelper: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug(self,msg):
	
	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)
	#def execute

	def _loadStore(self):
		action="load"
		epicList=self.epiManager.all_available_epis
		rebostPkgList=self._generateRebostFromEpic(epicList)
		if self._chkNeedUpdate(rebostPkgList):
			epicMd5=hashlib.md5(str(rebostPkgList).encode("utf-8")).hexdigest()
			with open(self.lastUpdate,'w') as f:
				f.write(epicMd5)
			self._debug("Sending {} to sql".format(len(rebostPkgList)))
			rebostHelper.rebostPkgsToSqlite(rebostPkgList,'zomandos.db')
		else:
			self._debug("Skip update")
	#def _loadStore

	def _chkNeedUpdate(self,rebostPkgList):
		update=True
		appMd5=""
		lastUpdate=""
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
		else:
			fcontent=""
			with open(self.lastUpdate,'r') as f:
				lastUpdate=f.read()
			epiMd5=hashlib.md5(str(rebostPkgList).encode("utf-8")).hexdigest()
			if epiMd5==lastUpdate:
				update=False
		return(update)
	#def _chkNeedUpdate

	def _getEpicZomandos(self):
		epicList=self.epiManager.all_available_epis
		for epic in epicList:
			self._debug("Available: {}".format(epic))
		return(epicList)
	#def _getEpicZomandos
	
	def _generateRebostFromEpic(self,epicList):
		rebostPkgList=[]
		for epi in epicList:
			for epiName,epiData in epi.items():
				self._debug("Processing {} ({})".format(epiName,len(epiData)))
				fname=epiData.get("zomando")
				if len(fname)>0:
					appFile=os.path.join(self.appDir,"{}.app".format(fname))
					rebostPkg=rebostHelper.rebostPkg()
					rebostPkg['name']=os.path.basename(fname).replace(".zmd","")
					rebostPkg['id']="zero.lliurex.{}".format(epiName)
					rebostPkg['pkgname']=fname
					rebostPkg['bundle']={"zomando":os.path.join(self.zmdDir,"{}.zmd".format(fname))}
					rebostPkg['homepage']="https://github.com/lliurex"
					rebostPkg['versions']={'zomando':self.release}
					rebostPkg['summary']=epiData.get("custom_name",rebostPkg["name"])
					rebostPkg['state']={"zomando":"1"}
					pkgList=epiData.get("pkg_list",[])
					pkgList.extend(epiData.get("only_gui_available",[]))
					if len(pkgList)>0:
						epiInfo=self._getEpiInfo(epiName,epiData["zomando"])
						for pkg in pkgList:
							if pkg["name"] not in epiInfo:
								continue
							print(pkg["name"])
							rebostPkgTmp=copy.deepcopy(rebostPkg)
							rebostPkgTmp["name"]=pkg.get("name").split(" ")[0].rstrip(",").rstrip(".").rstrip(":")
							rebostPkgTmp["pkgname"]=pkg.get("name")
							rebostPkgTmp['summary']=pkg.get("custom_name",pkg["name"])
							rebostPkgTmp['icon']=pkg.get("custom_icon",pkg["name"])
							state="1"
							#if epiInfo[pkg["name"]]['status']=="installed":
							#	state="0"
							bundle="package"
							epiType=epiInfo[pkg["name"]].get("type","apt")
							if epiType=="apt":
								bundle="package"
							elif epiType=="flatpak":
								bundle="flatpak"
							elif epiType=="snap":
								bundle="snap"
							elif epiType=="appimage":
								bundle="appimage"
							if bundle!="zomando":
								rebostPkgTmp['bundle'].update({bundle:rebostPkgTmp["pkgname"]})
								rebostPkgTmp['state']={bundle:state}
							#rebostPkgTmp['alias']=fname
							rebostPkgList.append(rebostPkgTmp)
							#Update master zmd description
							rebostPkg['description']+="<li> * {}</li>".format(pkg.get("custom_name",pkg["name"]))
						rebostPkgList.append(rebostPkg)
					else:
						print("No packages found for {}".format(fname))
		return(rebostPkgList)
	#def _generateRebostFromEpic

	def _getEpiInfo(self,epiName,zmdName):
		epiInfo={}
		zmdName=zmdName.replace(".epi","")
		epiPath=os.path.join("/","usr","share",zmdName,epiName)
		if os.path.exists(epiPath):
			with open (epiPath,"r") as f:
				epiInfo=json.load(f)
		pkgInfoList=epiInfo.get("pkg_list",[])
		for pkgItem in pkgInfoList:
			name=pkgItem.pop("name")
			epiInfo.update({name:pkgItem})
		#epiManager=epimanager.EpiManager()
		#if os.path.exists(icnPath):
		#	epiPath=os.path.join(os.path.dirname(icnPath),epiName)
		#	print(epiPath)
			#epiManager.read_conf(epiPath)
			#epiManager.get_pkg_info()
			#if hasattr(epiManager,"pkg_info"):
			#	epiInfo=epiManager.pkg_info
		return epiInfo
	#def _getEpiInfo

	def _getFileFromEpiF(self,epic,lstFiles):
		fname=""
		appname=epic.replace(".epi",".app")
		if appname not in lstFiles:
			for f in lstFiles:
				if f.endswith(appname):
					fname=f
					break
			if fname not in lstFiles:
				for f in lstFiles:
					if (appname.split(".")[0] in f) or (appname.split("-")[0] in f):
						fname=f
						break
		else:
			fname=appname
		if fname=="":
			fname=self._deepSearchForEpic(epic)
			self._debug("Deep Search for {} -> {}".format(epic,fname))
		return(fname)
	#def _getFileFromEpiF

	def _deepSearchForEpic(self,epicF):
		epiName=epicF
		for i in os.scandir(self.zmdDir):
			with open(i,"r") as f:
				fcontent=f.readlines()
			for fline in fcontent:
				if epicF in fline:
					epiName=i.name.replace(".zmd",".app")
		return(epiName)
	#def _deepSearchForEpic

	def _getDataForAllPackages(self,fname,rebostPkg):
		pkgList=[]
		rebostPkg=self._getAppData(fname,rebostPkg)
		pkgList=self._getZomandoInstalls(rebostPkg)
		return(pkgList)
	#def _getDataForAllPackages

	def _getAppData(self,fname,rebostPkg):
		appPath=os.path.join(self.appDir,fname)
		#REM THIS IS TIME CONSUMMING!!!
		rebostPkg=self._getDataFromSystem(rebostPkg)
		#rebostPkg=self._getDataFromAppFile(appPath,rebostPkg)
		rebostPkg['summary']=summary
		rebostPkg['description']=description
		if "Zomando" in rebostPkg['categories']:
			rebostPkg['categories'].remove("Zomando")
		rebostPkg['categories'].insert(0,"Zomando")
		if "Lliurex" in rebostPkg['categories']:
			rebostPkg['categories'].remove("Lliurex")
		rebostPkg['categories'].insert(0,"Lliurex")
		return(rebostPkg)
	#def _getAppData

	def _getStateFromSystem(self,rebostPkg):
		#state=self._getDataFromN4d(rebostPkg)
		#if state=="0":
		#REM THIS IS TIME CONSUMMING!!!
		#state=self._getDataFromEpic(rebostPkg)
		rebostPkg["state"].update({"zomando":state})
		return(rebostPkg)
	#def _getDataFromSystem

	def _getDataFromN4d(self,rebostPkg):
		zmd=rebostPkg["bundle"]["zomando"]
		zmdVars={}
		var={}
		try:
			zmdVars=self.n4d.get_variable("ZEROCENTER")
		except:
			time.sleep(1)
			try:
				zmdVars=self.n4d.get_variable("ZEROCENTER")
			except:
				print("N4D not reachable")
		state=1
		if isinstance(zmdVars,dict):
			var=zmdVars.get(rebostPkg["pkgname"],{})
		if (var.get('state',0)==1) or (os.path.isfile(zmd)):
			state="0"
		elif "state" in var.keys():
			state="1"
		return state
	#def _getDataFromN4d

	def _getDataFromEpic(self,rebostPkg):
		epi=""
		zmd=rebostPkg["bundle"].get("zomando","")
		if len(zmd)>0:
			with open(zmd,"r") as f:
				rawOutput=f.read()
			try:
				idx=rawOutput.index("epi-gtk")
			except:
				print("****************")
				print("****************")
				print("****************")
				print(rawOutput)
				print("****************")
				print("****************")
				print("****************")
				idx=-1
			if idx>0:
				epi=os.path.basename(rawOutput[idx:].split(" ")[1].split("\n")[0].strip())
				#for fline in f.readlines():
				#	if fline.startswith("epi-gtk"):
				#		epi=os.path.basename(fline.split(" ")[-1].strip())
		if len(epi)==0:
			epi="{}.epi".format(rebostPkg["name"]).strip()
		cmd=[EPIC,"showinfo","{}".format(epi)]
		proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
		rawoutput=proc.stdout
		rawStatus=""
		try:
			idx=rawoutput.index("- Status:")
		except:
			print(rawoutput)
			print("%{}%".format(epi))
		finally:
			if idx>0:
				rawStatus=rawoutput[idx:idx+rawoutput[idx:].index("\n")]
			if "installed" in rawStatus.lower():
				rebostPkg['state'].update({'zomando':0})
			else:
				rebostPkg['state'].update({'zomando':1})

	#	output=[line.strip() for line in rawoutput.split("\n")]
	#	for line in output:
	#		if ":" not in line:
	#			continue
	#		(key,item)=line.replace(" ","").split(":",1)
	#		if key.lower()=="-status":
	#			if item.lower()=="installed":
	#				rebostPkg['state'].update({'zomando':0})
	#			else:
	#				rebostPkg['state'].update({'zomando':1})
	#			break
		return(rebostPkg["state"]["zomando"])
	#def _getDataFromEpic

	def _getDataFromAppFile(self,appPath,rebostPkg):
		(icon,cat)=("","")
		description=""
		summary=""
		with open(appPath,'r') as f:
			fcontent=f.readlines()
			for fline in fcontent:
				if fline.startswith("Icon"):
					icon=fline.split("=")[-1].rstrip()
					if len(icon.split("."))<2:
						icon="{}.png".format(icon).rstrip()
					rebostPkg['icon']=os.path.join(self.iconDir,icon)
				elif fline.startswith("Category"):
					cat=fline.split("=")[-1].rstrip()
					if cat.lower()=="internet":
						cat="Network"
					elif cat.lower()=="support":
						cat="Software"
					if cat not in rebostPkg['categories'] and len(cat.strip())>0:
						rebostPkg['categories'].append(cat)
				elif fline.startswith("Name"):
					if summary=="":
						summary=fline.split("=")[-1].strip()
					if len(self.locales)>0:
						for locale in self.locales:
							if fline.startswith("Name[{}".format(locale)):
								summary=fline.split("=")[-1].strip()
								break
				elif fline.startswith("Comment"):
					if description=="":
						description=fline.split("=")[-1]
					if len(self.locales)>0:
						for locale in self.locales:
							if fline.startswith("Comment[{}".format(locale)):
								description=fline.split("=")[-1]
								break
			rebostPkg['summary']=summary
			rebostPkg['description']=description
			if "Zomando" in rebostPkg['categories']:
				rebostPkg['categories'].remove("Zomando")
			rebostPkg['categories'].insert(0,"Zomando")
			if "Lliurex" in rebostPkg['categories']:
				rebostPkg['categories'].remove("Lliurex")
			rebostPkg['categories'].insert(0,"Lliurex")
		return(rebostPkg)
	#def _getDataFromAppFile

	def _getPkgsFromList(self,pkgList,rebostPkg,jepi):
		pkgs=[]
		for pkg in pkgList:
			name=pkg.get("name","").strip()
			if "zero-lliurex-{}".format(name)==rebostPkg["name"]:
				self._debug("SKIP {} (duplicated of {})".format(name,rebostPkg["name"])) 
				continue
			if name.lower().startswith("lib"):
				continue
			if name.lower().endswith("libs"):
				continue
			rebostTmp={}
			rebostTmp=copy.deepcopy(rebostPkg)
			rebostTmp["name"]=self._getNameForPkg(name)
			rebostTmp["pkgname"]=name
			cname=pkg.get('custom_name','')
			if len(cname)<1:
				cname=pkg.get('name','')
			rebostTmp["description"]+="\\\\{}".format(cname.strip())
			rebostTmp=self._fillDataFromEpi(rebostTmp,pkg)
			if pkg.get("custom_icon","")!="":
				customIcon=os.path.join(jepi.get("epiPathDir",""),pkg.get("custom_icon"))
				if os.path.exists(customIcon):
					rebostTmp["icon"]=customIcon
				else:
					rebostTmp["icon"]=pkg.get("customIcon",rebostPkg["icon"])
			if "Zomando" in rebostTmp["categories"] and rebostTmp["name"]!=rebostPkg["name"]:
				rebostTmp["categories"].remove("Zomando")
			rebostTmp["state"].update({"zomando":rebostPkg["state"]["zomando"]})
			#rebostTmp["alias"]=rebostPkg["pkgname"]
			pkgs.append(rebostTmp)
		return(pkgs)
	#def _getPkgsFromList

	def _getZomandoInstalls(self,rebostPkg):
		pkgs=[]
		zmdPath=rebostPkg["bundle"]["zomando"]
		jepi=self._getJsonFromZmd(zmdPath)
		pkgList=jepi.get("pkg_list",[])
		#description=rebostPkg.get('description','')
		#origcats=rebostPkg.get('categories',[]).copy()
		#origstate=rebostPkg.get('state',{}).copy()
		if "Zomando" not in rebostPkg["categories"]:
			rebostPkg["categories"].insert(0,"Zomando")
		#Only more than one package
		if len(pkgList)>0:
			pkgs=self._getPkgsFromList(pkgList,rebostPkg,jepi)
			rebostPkg["description"]+="\\\\====="
			for pkg in pkgs:
				rebostPkg["description"]="{0}\\\\ {1}".format(rebostPkg["description"],pkg["name"])
			#rebostPkg["categories"]=origcats
			#rebostPkg["state"]=origstate
			#rebostPkg['description']=description.strip()
			pkgs.insert(0,rebostPkg)
		return(pkgs)
	#def _getZomandoInstalls

	def _getJsonFromZmd(self,zmdPath):
		epi=''
		jepi={}
		if os.path.isfile(zmdPath):
			with open(zmdPath,'r') as f:
				for fline in f.readlines():
					if fline.startswith("epi-gtk"):
						epi=fline.split(" ")[-1].strip()
						break
			if epi!='':
				if os.path.isfile(epi.strip()):
					jepi={}
					with open(epi.strip()) as f:
						try:
							jepi=json.load(f)
						except Exception as e:
							print(e)
							print("ERROR {}".format(epi))
		jepi.update({"epiPathDir":os.path.dirname(epi.strip())})
		return(jepi)
	#def _getJsonFromZmd

	def _getNameForPkg(self,name):
		nameComponents=name.lower().split(".")
		cont=len(nameComponents)-1
		banlist=["desktop","org","net","com"]
		name=nameComponents[-1].lower()
		while cont>=0:
			if nameComponents[cont].lower() not in banlist:
				name=nameComponents[cont].lower()
				break
			cont-=1
		return(name)
	#def _getNameForPkg

	def _fillDataFromEpi(self,rebostTmp,pkg):
		bundle=pkg.get("type","")
		if len(bundle)>0 and bundle in ["apt"]:
			bundle="package"
		elif bundle in ["file","deb"]:
			bundle=""
			rebostTmp["alias"]=rebostTmp["bundle"].get("zomando")
		if bundle!="":
			rebostTmp["bundle"].update({bundle:rebostTmp["name"]})
			rebostTmp["state"].update({bundle:"1"})
		#rebostTmp["state"].update({"zomando":"1"})
		return(rebostTmp)
	#def _fillDataFromEpi

#	def _fillDataFromEpi(self,rebostTmp,pkg):
#		bundle=pkg.get("type","")
#		if len(bundle)>0 and bundle in ["apt"]:
#			bundle="package"
#		elif bundle in ["file","deb"]:
#			bundle=""
#			key=pkg.get("key_store","")
#		if len(bundle)>0:
#			if len(key)>0:
#				zmd=os.path.join(self.zmdDir,"{}.zmd".format(key))
#				rebostTmp["bundle"].update({bundle:rebostTmp["alias"]})
#			try:
#				rebostTmp["bundle"].update({bundle:rebostTmp["alias"]})
#			except:
#				print("-------")
#				print(rebostTmp)
#				print("-------")
#			rebostTmp["state"].update({bundle:"1"})
#		#rebostTmp["state"].update({"zomando":"1"})
#		return(rebostTmp)
#	#def _fillDataFromEpi

	def getEpiForPkg(self,pkg):
		epi=pkg
		epicList=self._getEpicZomandos()
		rebostPkgList=self._generateRebostFromEpic(epicList)
		for rebostPkg in rebostPkgList:
			if rebostPkg["name"]!=pkg:
				continue
			epi=rebostPkg["bundle"].get("zomando","")
			if len(epi.strip())==0:
				if rebostPkg["id"].startswith("zero."):
					epi=rebostPkg["id"].split(".")[-1]
					break
			else:
				break
		return(epi)
	#def getEpiForPkg

	def getPkgEpiTree(self):
		epicList=self._getEpicZomandos()
		rebostPkgList=self._generateRebostFromEpic(epicList)
		tree={}
		for rebostPkg in rebostPkgList:
			tree[rebostPkg["name"]]=rebostPkg["bundle"].get("zomando","")
		return(tree)
	#def getPkgEpiTree
		
def main():
	obj=epicHelper()
	return (obj)

