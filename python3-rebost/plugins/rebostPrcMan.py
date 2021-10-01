#!/usr/bin/env python3
import os
import logging
import sqlHelper
from appconfig.appConfigN4d import appConfigN4d as n4d
import json
import rebostHelper
import subprocess

class rebostPrcMan():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		self.rebost=None
		self.actions=["install","remove","progress"]
		self.packagekind="*"
		self.enabled=True
		logging.basicConfig(format='%(message)s')
		self.sql=sqlHelper.sqlHelper()
		self.progress={}
		self.priority=100
		self.gui=False
		self.n4d=n4d()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			logging.warning("prcMan: %s"%str(msg))
	
	def execute(self,*argcc,action='',args='',extraArgs='',extraArgs2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='progress':
			rs=self._getProgress()
		if action=='insert':
			rs=self._insertProcess()
		if action=='remove' or action=='install':
			rs=self._managePackage(args,extraArgs,action)
		return(rs)
	#def execute

	def _getProgress(self):
		(db,cursor)=self.sql.enable_connection(self.sql.proc_table)
		query="SELECT * FROM rebostPrc;"
		self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		self.sql.close_connection(db)
		for row in rows:
			if isinstance(row,tuple):
				(pid,data)=row
				print(row)
				if os.path.exists(os.path.join("/proc/",pid)):
					#process running, update progress
					pass
				else:
					#process finished, invoke epi status
					print(data)
					for episcript,action in json.loads(data).items():
						self._debug("Select {} from {}".format(action,episcript))
						proc=subprocess.run([episcript,'getStatus'],stdout=subprocess.PIPE)
						stdout=proc.stdout.decode().strip()
						if action=='install' or action=='remove':
							if stdout=="0":
								self._debug("Uninstalled")
								if action=='install':
									query="UPDATE data from rebostPrc set values({}) where pkg={}".format(data,pid)
							else:
								self._debug("Installed")
		return(rows)
	#def _getProgress
	
	def _insertProcess(self,rebostPkgList):
		(db,cursor)=self.sql.enable_connection(self.sql.proc_table)
		for rebostPkg in rebostPkgList:
			(pkg,process)=rebostPkg
			query="INSERT INTO rebostPrc (pkg,data) VALUES ('{}', '{}') ON CONFLICT(pkg) DO UPDATE SET pkg='{}';".format(process.get('pid'),str(json.dumps({process.get('script'):process.get('status')})),process.get('pid'))
			self._debug(query)
			try:
				cursor.execute(query)
			except Exception as e:
				print("{}".format(e))
		self.sql.close_connection(db)
		return('[{}]')
	#def _insertProcess
	
	def _managePackage(self,pkgname,bundle='',action='install'):
		self._debug("{} package {}".format(action,pkgname))
		rebostPkgList=[]
		rebostpkg=''
		#1st search that there's a package in the desired format
		rows=self.sql.execute(action='show',args=pkgname)
		if rows and isinstance(rows,list):
			(package,rebostpkg)=rows[0]
			bundles=json.loads(rebostpkg).get('bundle',"not found")
			if len(bundles)>1:
				if not (bundle and bundle in bundles):
					rebostpkg=''
					if bundle:
						rebostPkgList=[("-1",{'package':package,'status':'not available as {}, only as {}'.format(bundle," ".join(list(bundles.keys())))})]
					else:
						rebostPkgList=[("-1",{'package':package,'status':'available from many sources, please choose one from: {}'.format(" ".join(list(bundles.keys())))})]
			else:
				bundle=list(bundles.keys())[0]
		else:
			rebostPkgList=[("-1",{'package':package,'status':'package {} not found'.format(pkgname)})]
		if rebostpkg:
		#Well, almost the package exists and the desired format is available so generate EPI files and return.
			(epifile,episcript)=rebostHelper.generate_epi_for_rebostpkg(rebostpkg,bundle)
			rebostPkgList=[(pkgname,{'package':pkgname,'status':action,'epi':epifile})]
			#subprocess.run(['pkexec','epi-gtk',epifile])
			self._debug("Executing N4d query")
			pid=self.n4d.n4dQuery("LliurexStore","{}_epi".format(action),epifile,self.gui)
			rebostPkgList=[(pkgname,{'package':pkgname,'status':action,'epi':epifile,'script':episcript,'pid':pid})]
			self._insertProcess(rebostPkgList)

		self._debug(rebostPkgList)
		return (rebostPkgList)
	#def _managePackage


def main():
	obj=rebostPrcMan()
	return (obj)
