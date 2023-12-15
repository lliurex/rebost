#!/usr/bin/env python3
import os
import json
import tempfile
import rebostHelper
import logging
import locale
import n4d.client as n4d

class zomandoHelper():
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
		self.n4d=n4d.Client()
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="zomando: {}".format(msg)
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
		self._get_zomandos()
	#def _loadStore

	def _get_zomandos(self):
		self._debug("Loading store")
		rebostPkgList=[]
		seen=[]
		if os.path.isdir(self.zmdDir):
			self._debug("Processing {}".format(self.zmdDir))
			for f in os.listdir(self.zmdDir):
				if f.endswith(".zmd"):
					rebostPkg=rebostHelper.rebostPkg()
					appName=os.path.basename(f).replace(".zmd","")
					if appName not in seen:
						seen.append(appName)
					else:
						continue
					rebostPkg['name']=appName
					rebostPkg['pkgname']=appName
					rebostPkg=self.fillData(f,rebostPkg)
					if isinstance(rebostPkg,dict):
						rebostPkgList.append(rebostPkg)
			self._debug("Processing {}".format(self.appDir))
			for f in os.listdir(self.appDir):
				if f.endswith(".app"):
					rebostPkg=rebostHelper.rebostPkg()
					appName=os.path.basename(f).replace(".app","")
					if appName not in seen:
						seen.append(appName)
					else:
						continue
					rebostPkg['name']=appName
					rebostPkg['pkgname']=appName
					rebostPkg=self.fillData(f,rebostPkg)
					if isinstance(rebostPkg,dict):
						rebostPkgList.append(rebostPkg)
		if rebostPkgList:
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'zomandos.db')
			self._debug("SQL Loaded")
	#def _get_zomandos

	def fillData(self,zmd,rebostPkg):
		appName=os.path.basename(zmd).replace(".zmd",".app")
		appPath=os.path.join(self.appDir,appName)
		description=''
		summary=''
		rebostPkg=self._get_zomando_data(zmd,rebostPkg)
		if  "Zomando" in rebostPkg.get('categories',[]):
			if len(summary)>0 and rebostPkg['summary']=='': 
				rebostPkg['summary']=summary
			if len(description)>0 and rebostPkg['description']=='': 
				rebostPkg['description']=description
			rebostPkg['license']="GPL-3"
			rebostPkg['homepage']="https://www.github.com/lliurex"
			rebostPkg['bundle'].update({'zomando':'{}'.format(zmd)})
			rebostPkg['versions']={'zomando':'1'}
		else:
			rebostPkg=None
		return(rebostPkg)
	#def fillData

	def _get_zomando_data(self,zmd,rebostPkg):
		appName=os.path.basename(zmd).replace(".zmd",".app")
		appPath=os.path.join(self.appDir,appName)
		groupsProcessed=False
		if os.path.isfile(appPath):
			rebostPkg['state'].update({'zomando':self._get_zomando_state(zmd)})
			if rebostPkg['state'].get('zomando','')=="0": 
				rebostPkg['installed'].update({'zomando':"1"})
			(icon,cat)=("","")
			with open(appPath,'r') as f:
				for fline in f.readlines():
					if fline.startswith("Icon"):
						icon=fline.split("=")[-1].rstrip()
						if len(icon.split("."))<2:
							icon="{}.png".format(icon).rstrip()

						rebostPkg['icon']=os.path.join(self.iconDir,icon)
					elif fline.startswith("Category"):
						cat=fline.split("=")[-1].rstrip()
						if cat.lower() in ['software','fp','resources','multimedia','support','internet'] and cat not in rebostPkg['categories']:
							if cat.lower()=="internet":
								cat="Network"
							elif cat.lower()=="support":
								cat="Software"
							if cat not in rebostPkg['categories']:
								rebostPkg['categories'].append(cat)
							if "Zomando" not in rebostPkg['categories']:
								rebostPkg['categories'].append("Zomando")
							rebostPkg['categories'].append("Lliurex")
						else:
							rebostPkg['categories']=["System"]
					elif fline.startswith("Name"):
							summary=fline.split("=")[-1]
							if len(self.locale)>0:
								if fline.startswith("Name[{}".format(self.locale)):
									rebostPkg['summary']=summary
					elif fline.startswith("Comment"):
							description=fline.split("=")[-1]
							if len(self.locale)>0:
								if fline.startswith("Comment[{}".format(self.locale)):
									description=fline.split("=")[-1]
							rebostPkg['description']=description
					elif fline.startswith("Groups"):
							groups=fline.split("=")[-1].strip()
							if '*' in groups or "students" in groups or "teachers" in groups:
								groupsProcessed=True
		if groupsProcessed==False:
			rebostPkg['categories']=["System"]
		else:
			rebostPkg=self._get_zomando_installs(zmd,rebostPkg)
		return(rebostPkg)

	def _get_zomando_installs(self,zmd,rebostPkg):
		zmdPath=os.path.join(self.zmdDir,zmd)
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

	def _get_zomando_state(self,zmd):
		zmdVars={}
		if zmd.endswith(".zmd")==False:
			zmd="{}.zmd".format(zmd)
		try:
			zmdVars=self.n4d.get_variable("ZEROCENTER")
		except:
			time.sleep(1)
			try:
				zmdVars=self.n4d.get_variable("ZEROCENTER")
			except:
				print("N4D not reachable")
		zmdName=os.path.basename(zmd).replace(".zmd","")
		if self.zmdDir not in zmd:
			zmd=os.path.join(self.zmdDir,zmd)
		state="1"
		var={}
		if isinstance(zmdVars,dict):
			var=zmdVars.get(zmdName,{})
		if (var.get('state',0)==1) or (os.path.isfile(zmd)):
			state="0"
		return state
	#def _get_zomando_state(self,zmd):

def main():
	obj=zomandoHelper()
	return (obj)

