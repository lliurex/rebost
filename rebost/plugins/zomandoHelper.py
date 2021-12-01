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
		self.n4d=n4d.Client()
#		self._loadStore()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("zomando: %s"%str(msg))
	
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

	def _get_zomandos(self):
		self._debug("Loading store")
		rebostPkgList=[]
		if os.path.isdir(self.zmdDir):
			for f in os.listdir(self.zmdDir):
				if f.endswith(".zmd"):
					self._debug("Processing {}".format(f))
					appName=os.path.basename(f).replace(".zmd","")
					rebostPkg=rebostHelper.rebostPkg()
					rebostPkg['name']=appName
					rebostPkg['pkgname']=appName
					rebostPkg['bundle'].update({'zomando':f})
					rebostPkg=self.fillData(f,rebostPkg)
					rebostPkgList.append(rebostPkg)
		if rebostPkgList:
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'zomandos.db')
			self._debug("SQL Loaded")

	def fillData(self,zmd,rebostPkg):
		appName=os.path.basename(zmd).replace(".zmd",".app")
		appPath=os.path.join(self.appDir,appName)
		self._debug("Path: {}".format(appPath))
		if os.path.isfile(appPath):
			rebostPkg['state'].update({'zomando':self._get_zomando_state(zmd)})
		return(rebostPkg)

	def _get_zomando_state(self,zmd):
		zmdVars=self.n4d.get_variable("ZEROCENTER")
		zmdName=os.path.basename(zmd).replace(".zmd","")
		state=""
		if isinstance(zmdVars,dict):
			var=zmdVars.get(zmdName,{})
			state=var.get('state','0')
			if state==1:
				state=0
			else:
				state=1
		return (str(state))


	

def main():
	obj=zomandoHelper()
	return (obj)

