#!/usr/bin/env python3
import os
import json
import tempfile
import rebostHelper
import logging
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
		self.n4d=n4d.Client()
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="zomando: %s".format(msg)
			rebostHelper,_debug(dbg)
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
		if os.path.isdir(self.zmdDir):
			self._debug("Processing {}".format(self.zmdDir))
			for f in os.listdir(self.zmdDir):
				if f.endswith(".zmd"):
					rebostPkg=rebostHelper.rebostPkg()
					appName=os.path.basename(f).replace(".zmd","")
					rebostPkg['name']=appName
					rebostPkg['pkgname']=appName
					rebostPkg=self.fillData(f,rebostPkg)
					rebostPkgList.append(rebostPkg)
		if rebostPkgList:
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'zomandos.db')
			self._debug("SQL Loaded")
	#def _get_zomandos

	def fillData(self,zmd,rebostPkg):
		appName=os.path.basename(zmd).replace(".zmd",".app")
		appPath=os.path.join(self.appDir,appName)
		rebostPkg['categories'].append("Zomando")
		if os.path.isfile(appPath):
			rebostPkg['state'].update({'zomando':self._get_zomando_state(zmd)})
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
						if cat!='Category' and cat not in rebostPkg['categories']:
							rebostPkg['categories'].append(cat)
					if icon and cat:
						break

		rebostPkg['categories'].append('Lliurex')
		rebostPkg['license']="GPL-3"
		rebostPkg['homepage']="https://www.github.com/lliurex"
		rebostPkg['bundle'].update({'zomando':'{}'.format(zmd)})
		return(rebostPkg)
	#def fillData

	def _get_zomando_state(self,zmd):
		zmdVars=self.n4d.get_variable("ZEROCENTER")
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

