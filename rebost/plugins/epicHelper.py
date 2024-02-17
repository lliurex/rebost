#!/usr/bin/env python3
import os,distro
import json
import tempfile
import rebostHelper
import logging
import locale
import n4d.client as n4d
import subprocess

EPIC="/usr/sbin/epic"

class epicHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
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
		self.n4d=n4d.Client()
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="zomando: {}".format(msg)
			#rebostHelper._debug(dbg)
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
		self._debug("Sending {} to sql".format(len(rebostPkgList)))
		rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'zomandos.db')
	#def _loadStore

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
				if  fname not in lstFiles:
					continue
			self._debug("Match {}%".format(fname))
			rebostPkg=rebostHelper.rebostPkg()
			rebostPkg['name']=os.path.basename(fname).replace(".app","")
			rebostPkg['id']="zero.lliurex.{}".format(epic.replace(".epi",""))
			rebostPkg['pkgname']=os.path.basename(fname).replace(".app","")
			rebostPkg['bundle']={"zomando":os.path.join(self.zmdDir,fname.replace(".app",".zmd"))}
			rebostPkg=self._getAppData(fname,rebostPkg)
			rebostPkgList.append(rebostPkg)
		return(rebostPkgList)
	#def _generateRebostFromEpic

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
		state=None
		if isinstance(zmdVars,dict):
			var=zmdVars.get(rebostPkg["pkgname"],{})
		if (var.get('state',0)==1) or (os.path.isfile(zmd)):
			state="0"
		elif "state" in var.keys():
			state="1"
		return state
	#def _get_zomando_state(self,zmd):

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
					rebostPkg['state'].update({'zomando':1})
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
					if cat not in rebostPkg['categories']:
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
			if "Zomando" not in rebostPkg['categories']:
				rebostPkg['categories'].append("Zomando")
			if "Lliurex" not in rebostPkg['categories']:
				rebostPkg['categories'].insert(0,"Lliurex")
			rebostsPkg=self._getZomandoInstalls(rebostPkg)
		return(rebostPkg)
	#def _getDataFromAppFile

	def _getZomandoInstalls(self,rebostPkg):
		zmdPath=rebostPkg["bundle"]["zomando"]
		epi=''
		if os.path.isfile(zmdPath):
			with open(zmdPath,'r') as f:
				for fline in f.readlines():
					if fline.startswith("epi-gtk"):
						epi=fline.split(" ")[-1]
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
					if jepi.get("pkg_list",[])!=[]:
						description=rebostPkg.get('description','')
						if len(jepi["pkg_list"])>1:
							for pkg in jepi["pkg_list"]:
								cname=pkg.get('custom_name','')
								if len(cname)<1:
									cname=pkg.get('name','')
								description+="\\\\{}".format(cname.strip())
						rebostPkg['description']=description.strip()
		return(rebostPkg)
	#def _getZomandoInstalls

def main():
	obj=epicHelper()
	return (obj)

