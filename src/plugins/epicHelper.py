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
		self.user=''
		if kwargs:
			self.user=kwargs.get('user','')
		self.zmdDir="/usr/share/zero-center/zmds"
		self.appDir="/usr/share/zero-center/applications"
		self.iconDir="/usr/share/banners/lliurex-neu/"
		self.locale=locale.getlocale()[0].split("_")[0]
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
		epicList=self._getEpicZomandos()
		rebostPkgList=self._generateRebostFromEpic(epicList)
		if self._chkNeedUpdate(rebostPkgList):
			epicMd5=hashlib.md5(str(rebostPkgList).encode("utf-8")).hexdigest()
			with open(self.lastUpdate,'w') as f:
				f.write(epicMd5)
			self._debug("Sending {} to sql".format(len(rebostPkgList)))
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'zomandos.db')
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
		cmd=[EPIC,"showlist"]
		epicList=[]
		renv = os.environ.copy()
		if len(renv.get("USER",""))==0:
			renv["USER"]="root"
		proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,env=renv)
		output=proc.stdout
		if "EPIC:" in output:
			idx=output.index("EPIC:")
			rawEpicList=output[idx:].replace("EPIC:","")
			epicList=[ epic.strip() for epic in rawEpicList.split(",") ]
		return(epicList)
	#def _getEpicZomandos
	
	def _generateRebostFromEpic(self,epicList):
		lstFiles=[]
		rebostPkgList=[]
		if os.path.isdir(self.appDir):
			lstFiles=os.listdir(self.appDir)
		for epic in epicList:
			self._debug("Processing {}".format(epic))
			fname=self._getFileFromEpiF(epic,lstFiles)
			if  fname not in lstFiles:
					continue
			self._debug("Match {}%".format(fname))
			rebostPkg=rebostHelper.rebostPkg()
			rebostPkg['name']=os.path.basename(fname).replace(".app","")
			rebostPkg['id']="zero.lliurex.{}".format(epic.replace(".epi",""))
			rebostPkg['pkgname']=os.path.basename(fname).replace(".app","")
			rebostPkg['bundle']={"zomando":os.path.join(self.zmdDir,fname.replace(".app",".zmd"))}
			rebostPkg['homepage']="https://github.com/lliurex"
			rebostPkg['versions']={'zomando':self.release}
			rebostPkgList.extend(self._getDataForAllPackages(fname,rebostPkg))
		return(rebostPkgList)
	#def _generateRebostFromEpic

	def _getFileFromEpiF(self,epic,lstFiles):
		fname=epic.replace(".epi",".app")
		if fname not in lstFiles:
			for f in lstFiles:
				if f.endswith(fname):
					fname=f
					break
			if  fname not in lstFiles:
				for f in lstFiles:
					if (fname.split(".")[0] in f) or (fname.split("-")[0] in f):
						fname=f
						break
		return(fname)
	#def _getFileFromEpiF

	def _getDataForAllPackages(self,fname,rebostPkg):
		pkgList=[]
		rebostPkg=self._getAppData(fname,rebostPkg)
		pkgList=self._getZomandoInstalls(rebostPkg)
		return(pkgList)
	#def _getDataForAllPackages

	def _getAppData(self,fname,rebostPkg):
		appPath=os.path.join(self.appDir,fname)
		rebostPkg=self._getDataFromSystem(rebostPkg)
		rebostPkg=self._getDataFromAppFile(appPath,rebostPkg)
		return(rebostPkg)
	#def _getAppData

	def _getDataFromSystem(self,rebostPkg):
		state=self._getDataFromN4d(rebostPkg)
		if state==None:
			state=self._getDataFromEpic(rebostPkg)
		rebostPkg["state"]={"zomando":state}
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
		cmd=[EPIC,"showinfo","{}.epi".format(rebostPkg["name"])]
		proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
		rawoutput=proc.stdout
		output=[line.strip() for line in rawoutput.split("\n")]
		for line in output:
			if ":" not in line:
				continue
			(key,item)=line.replace(" ","").split(":",1)
			if key.lower()=="-status":
				if item.lower()=="installed":
					rebostPkg['state'].update({'zomando':0})
					break
		return(rebostPkg)
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
						summary=fline.split("=")[-1]
					if len(self.locale)>0:
						if fline.startswith("Name[{}".format(self.locale)):
							summary=fline.split("=")[-1]
				elif fline.startswith("Comment"):
					if description=="":
						description=fline.split("=")[-1]
					if len(self.locale)>0:
						if fline.startswith("Comment[{}".format(self.locale)):
							description=fline.split("=")[-1]
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
		if len(pkgList)>1:
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
			rebostTmp["bundle"]={}
		if bundle!="":
			rebostTmp["bundle"].update({bundle:rebostTmp["name"]})
			rebostTmp["state"].update({bundle:"1"})
		#rebostTmp["state"].update({"zomando":"1"})
		return(rebostTmp)
	#def _fillDataFromEpi

def main():
	obj=epicHelper()
	return (obj)

