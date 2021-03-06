#!/usr/bin/env python3
import os,shutil
import logging
import sqlHelper
from appconfig.appConfigN4d import appConfigN4d as n4dClient
import json
import rebostHelper
import subprocess
import time
import random

class rebostPrcMan():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.rebost=None
		self.actions=["remote","test","install","remove","progress"]
		self.packagekind="*"
		self.enabled=True
		logging.basicConfig(format='%(message)s')
		self.sql=sqlHelper.sqlHelper()
		self.failProc=0
		if os.path.isfile(self.sql.proc_table):
			os.remove(self.sql.proc_table)
		self.user=''
		if self.user:
			self.appimageDir=os.getenv("HOME")+"/.local/bin"
		else:
			self.appimageDir="/opt/appimages"
		self.priority=100
		self.gui=False
		self.n4dClients={}

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			logging.warning("prcMan: %s"%str(msg))

	def _print(self,msg):
		logging.warning("prcMan: %s"%str(msg))
	
	def execute(self,*argcc,action='',parms='',extraParms='',extraParms2='',**kwargs):
		rs='[{}]'
		user=''
		n4dkey=''
		if kwargs:
			user=kwargs.get('user','')
			n4dkey=kwargs.get('n4dkey','')
		if action=='progress':
			rs=self._getProgress()
		if action=='insert':
			rs=self._insertProcess()
		if action in ['remove','install','test','remote']:
			if action=='remote':
				rs=self._managePackage(parms,extraParms,action,user=user,remote=True,n4dkey=n4dkey)
			else:
				rs=self._managePackage(parms,extraParms,action,user=user,n4dkey=n4dkey)
		return(rs)
	#def execute

	def _getProgress(self):
		(db,cursor)=self.sql.enableConnection(self.sql.proc_table)
		query="SELECT * FROM rebostPrc;"
		cursor.execute(query)
		rows=cursor.fetchall()
		progressArray=[]
		for row in rows:
			progress=()
			progress=row
			if isinstance(row,tuple):
				(pid,data)=row
				data=json.loads(data).copy()
				if not data.get('done',None):
					if os.path.exists(os.path.join("/proc/",pid)):
						progress=(pid,self._getFakePercent(data))
						fstat=os.path.join("/proc/",pid,"stat")
						if os.path.isfile(fstat)==True:
							with open(fstat,'r') as f:
								flines=f.readlines()
								if "Z" == flines[0].split(" ")[2]:
									dataTmp=self._getEpiState(data)
									dataTmp['done']=1
									data['status']=dataTmp.get('status',-1)
									query="UPDATE rebostPrc set data='{}' where pkg='{}'".format(str(json.dumps(dataTmp)),pid)
									cursor.execute(query)
									self._debug("Z proc")
					else:
						dataTmp=self._getEpiState(data)
						data['status']=dataTmp.get('status',-1)
						dataTmp['done']=1
						query="UPDATE rebostPrc set data='{}' where pkg='{}'".format(str(json.dumps(dataTmp)),pid)
						cursor.execute(query)
						self.sql.execute(action='commitInstall',parms=dataTmp['package'],extraParms=dataTmp.get('bundle',"package"),extraParms2=dataTmp['status'])
						progress=(pid,dataTmp)

				else:
					dataTmp=self._getEpiState(data)
					self.sql.execute(action='commitInstall',parms=dataTmp['package'],extraParms=dataTmp.get('bundle',"package"),extraParms2=dataTmp['status'])
					episcript=data.get('episcript','')
					self._removeTempDir(episcript)
			
			else:
				if data.get('msg',''):
    					progress=(pid,data)
			progressArray.append(progress)
		self.sql.closeConnection(db)
		return(progressArray)
	#def _getProgress

	def _getFakePercent(self,data):
		max_time=1000
		runningTime=int(time.time())-int(data['time'])
		currentTime=int(time.time())
		estimatedTime=120
		#Real progress is unknown so fake it
		firstStep=int(random.randrange(20,30))
		secondStep=int(random.randrange(firstStep+1,80))
		thirdStep=100-(firstStep+secondStep)
		progressSteps=[firstStep,secondStep,thirdStep]
		for step in progressSteps:
		#Update percentage.
		#Fake a progress percentage (unimplemented).
		#process running, update progress
			if estimatedTime<step:
				estimatedTime=step+10
			seconds=int((step*estimatedTime)/100)
			#print("Step seconds: {}".format(seconds))
			#print("Running seconds: {}".format(runningTime))
			if runningTime>seconds and step<max_time:
				continue
			stepPercentage=((runningTime*100/seconds))
			#print("Step percentage: {}".format(stepPercentage))
			pending=int((step*stepPercentage)/100)
			#print("Total: {}".format(pending))
			data['status']=int(pending)
			break
		return data

	def _getEpiState(self,data):
		#process finished, invoke epi status
		action=data.get('action','')
		episcript=data.get('episcript','')
		epijson=episcript.replace("_script.sh",".epi")

		if action=='install' or action=='remove':
			if os.path.exists(episcript):
				stdout=rebostHelper.get_epi_status(data.get('episcript'))
				if action=='install' or action=='remove':
					if stdout=="0":
						if action=='install':
							data['status']='0'
						else:
							data['status']='-1'
					else:
						if action=='remove':
							data['status']='1'
						else:
							data['status']='-1'
		return data
	
	def _insertProcess(self,rebostPkgList):
		(db,cursor)=self.sql.enableConnection(self.sql.proc_table)
		for rebostPkg in rebostPkgList:
			(pkg,process)=rebostPkg
			query="INSERT INTO rebostPrc (pkg,data) VALUES ('{}', '{}') ON CONFLICT(pkg) DO UPDATE SET pkg='{}';".format(process.get('pid'),str(json.dumps({'episcript':process.get('script'),'status':process.get('status'),'bundle':process.get('bundle',''),'package':process.get('package',''),'action':process.get('action'),'time':int(time.time())})),process.get('pid'))
			self._debug(query)
			try:
				cursor.execute(query)
			except Exception as e:
				print("{}".format(e))
		self.sql.closeConnection(db)
		return('[{}]')
	#def _insertProcess
	
	def _chk_pkg_format(self,pkgname,bundle):
		rebostpkg=''
		rebostPkgList=[]
		rows=self.sql.execute(action='show',parms=pkgname)
		if rows and isinstance(rows,list):
			(package,rebostpkg)=rows[0]
			try:
				bundles=json.loads(rebostpkg).get('bundle',"not found")
			except Exception as e:
				if isinstance(rebostpkg,dict):
					bundles=rebostpkg.get('bundle',"not found")
				else:
					self._debug(e)

			if len(bundles)>0:
				self.failProc+=1
				if not (bundle and bundle in bundles):
					if bundle:
						rebostpkg=''
						rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'not available as {}, only as {}'.format(bundle," ".join(list(bundles.keys())))})]
					else:
						if len(bundles)>1:
							rebostpkg=''
							rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'available from many sources, please choose one from: {}'.format(" ".join(list(bundles.keys())))})]
						else:
							bundle=list(bundles.keys())[0]
			else:
				rebostpkg=''
				rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'not available as {}'.format(bundles)})]
		else:
			rebostpkg=''
			rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':pkgname,'done':1,'status':'','msg':'package {} not found'.format(pkgname)})]
		return(rebostpkg,bundle,rebostPkgList)
	#def _chk_pkg_format

	def _managePackage(self,pkgname,bundle='',action='install',user='',remote=False,n4dkey=''):
		self._debug("{} package {} as bundle {} for user {}".format(action,pkgname,bundle,user))
		#1st search that there's a package in the desired format
		(rebostpkg,bundle,rebostPkgList)=self._chk_pkg_format(pkgname,bundle)
		if rebostpkg:
		#Well, the package almost exists and the desired format is available so generate EPI files and return.
		#1st check if removing and if removing package doesn't removes meta
			sure=True
			if (action=='remove' or action=='test') and bundle=='package':
				if rebostHelper.check_remove_unsure(pkgname):
					rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':pkgname,'done':1,'status':'','msg':'package {} is a system package'.format(pkgname)})]
					sure=False
			#else:
			if sure:
				usern="{}".format(user)
				remote=False
				if action=="remote":
					remote=True
				self._debug("USER: {}".format(user))
				(epifile,episcript)=rebostHelper.generate_epi_for_rebostpkg(rebostpkg,bundle,user,remote)
				rebostPkgList=[(pkgname,{'package':pkgname,'status':action,'epi':epifile,'script':episcript,'bundle':bundle})]
				if usern in self.n4dClients.keys():
					n4d=self.n4dClients.get(usern)
					self._print("Select n4d proxy")
				else:
					n4d=n4dClient(username=usern)
					self.n4dClients.update({usern:n4d})
					self._print("Add n4d proxy")
				if action!='test' and remote==False:
					self._debug("Executing N4d query as user {}".format(user))
					if n4dkey:
						n4d.setCredentials(n4dkey=n4dkey)
					pid=n4d.n4dQuery("Rebost","{}_epi".format(action),epifile,self.gui,username=usern)
					if isinstance(pid,dict):
						pid=pid.get('status',-1)
					rebostPkgList=[(pkgname,{'package':pkgname,'action':action,'status':action,'epi':epifile,'script':episcript,'pid':pid,'bundle':bundle})]
					self._insertProcess(rebostPkgList)
				elif remote==True:
					if n4dkey:
						n4d.setCredentials(n4dkey=n4dkey)
					pid=n4d.n4dQuery("Rebost","remote_install",episcript,self.gui,username=usern)
					#pid=self.n4d.n4dQuery("Rebost","remote_install",episcript,self.gui)
					self._removeTempDir(episcript)

		self._debug(rebostPkgList)
		return (rebostPkgList)
	#def _managePackage

	def _removeTempDir(self,tmpfile):
			tmpDir=os.path.dirname(tmpfile)
#			files=[]
#			save_del=False
#			if os.path.isdir(tmpDir)==True:
#				files=os.listdir(os.path.dirname(tmpfile))
#				save_del=True
#			for f in files:
#				if os.path.join(tmpDir,f) not in [episcript,epijson]:
#					self._debug("Remove not possible: {} not in {} nor {}".format(f,episcript,epijson))
#					save_del=False
#					break
#			if save_del:
			if os.path.isdir(tmpDir):
				try:
					self._print("Removing tmp dir {}".format(tmpDir))
					shutil.rmtree(tmpDir)
				except Exception as e:
					self._debug("Couldn't remove tmpdir {}: {}".format(tmpDir,e))

def main():
	obj=rebostPrcMan()
	return (obj)
