#!/usr/bin/env python3
import os
import logging
import sqlHelper
from appconfig.appConfigN4d import appConfigN4d as n4d
import json
import rebostHelper
import subprocess
import time

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
	
	def execute(self,*argcc,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='progress':
			rs=self._getProgress()
		if action=='insert':
			rs=self._insertProcess()
		if action=='remove' or action=='install':
			rs=self._managePackage(parms,extraParms,action)
		return(rs)
	#def execute

	def _getProgress(self):
		(db,cursor)=self.sql.enable_connection(self.sql.proc_table)
		query="SELECT * FROM rebostPrc;"
		self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		progressArray=[]
		for row in rows:
			progress=()
			progress=row
			if isinstance(row,tuple):
				(pid,data)=row
				if os.path.exists(os.path.join("/proc/",pid)):
					dataTmp=json.loads(data).copy()
					max_time=1000
					runningTime=int(time.time())-int(dataTmp['time'])
					currentTime=int(time.time())
					estimatedTime=120
					progressSteps=[5,10,15,20,25,30,35,40,45,50,55,60,65,70,max_time]
					for step in progressSteps:
					#Update percentage.
					#Fake a progress percentage (unimplemented).
					#process running, update progress
						seconds=int((step*estimatedTime)/100)
						print("Step seconds: {}".format(seconds))
						print("Running seconds: {}".format(runningTime))
						if runningTime>seconds and step<max_time:
							continue
						stepPercentage=((runningTime*100/seconds))
						print("Step percentage: {}".format(stepPercentage))
						pending=int((step*stepPercentage)/100)
						print("Total: {}".format(pending))
						dataTmp['status']=int(pending)
						print(progress)
						progress=(pid,dataTmp)
						break
				else:
					#process finished, invoke epi status
					dataTmp=json.loads(data).copy()
					action=dataTmp.get('status','')
					if action=='install' or action=='remove':
						self._debug("Select {} from {}".format(action,dataTmp.get('episcript','')))
						if dataTmp.get('episcript',None):
							stdout=rebostHelper.get_epi_status(dataTmp.get('episcript'))
							if action=='install' or action=='remove':
								if stdout=="0":
									if action=='install':
										dataTmp['status']='0'
									else:
										dataTmp['status']='-1'
								else:
									if action=='remove':
										dataTmp['status']='1'
									else:
										dataTmp['status']='-1'
								query="UPDATE rebostPrc set data='{}' where pkg='{}'".format(str(json.dumps(dataTmp)),pid)
								cursor.execute(query)
								self.sql.execute(action='commitInstall',parms=dataTmp['package'],extraParms=dataTmp.get('bundle',"package"),extraParms2=dataTmp['status'])
						progress=(pid,dataTmp)
			progressArray.append(progress)
		self.sql.close_connection(db)
		return(progressArray)
	#def _getProgress
	
	def _insertProcess(self,rebostPkgList):
		(db,cursor)=self.sql.enable_connection(self.sql.proc_table)
		for rebostPkg in rebostPkgList:
			(pkg,process)=rebostPkg
			query="INSERT INTO rebostPrc (pkg,data) VALUES ('{}', '{}') ON CONFLICT(pkg) DO UPDATE SET pkg='{}';".format(process.get('pid'),str(json.dumps({'episcript':process.get('script'),'status':process.get('status'),'bundle':process.get('bundle',''),'package':process.get('package',''),'time':int(time.time())})),process.get('pid'))
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
		rows=self.sql.execute(action='show',parms=pkgname)
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
			rebostPkgList=[("-1",{'package':pkgname,'status':'package {} not found'.format(pkgname)})]
		if rebostpkg:
		#Well, the package almost exists and the desired format is available so generate EPI files and return.
			(epifile,episcript)=rebostHelper.generate_epi_for_rebostpkg(rebostpkg,bundle)
			rebostPkgList=[(pkgname,{'package':pkgname,'status':action,'epi':epifile,'bundle':bundle})]
			#subprocess.run(['pkexec','epi-gtk',epifile])
			self._debug("Executing N4d query")
			pid=self.n4d.n4dQuery("LliurexStore","{}_epi".format(action),epifile,self.gui)
			rebostPkgList=[(pkgname,{'package':pkgname,'status':action,'epi':epifile,'script':episcript,'pid':pid,'bundle':bundle})]
			self._insertProcess(rebostPkgList)

		self._debug(rebostPkgList)
		return (rebostPkgList)
	#def _managePackage


def main():
	obj=rebostPrcMan()
	return (obj)
