#!/usr/bin/env python3
import os,shutil
import sqlHelper
import json
import rebostHelper
import subprocess
import n4d.server.core as n4dcore
import multiprocessing
import threading
import time
import random

class rebostPrcMan():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.rebost=None
		self.actions=["remote","test","install","remove","progress"]
		self.packagekind="*"
		self.enabled=True
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
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _log(self,msg):
		dbg="prcMan: {}".format(msg)
		rebostHelper.logmsg(dbg)
	#def _log

	def _debug(self,msg):
		if self.dbg:
			dbg="prcMan: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug

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
					episcript=data.get('episcript','')
					if os.path.isfile(episcript):
						dataTmp=self._getEpiState(data)
						self.sql.execute(action='commitInstall',parms=dataTmp['package'],extraParms=dataTmp.get('bundle',"package"),extraParms2=dataTmp['status'])
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
		firstStep=int(random.randrange(10,20))
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
			#print("Being seconds: {}".format(currentTime))
			#print("Running seconds: {}".format(runningTime))
			if runningTime>seconds and step<max_time:
				continue
			stepPercentage=(runningTime*100/seconds)
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
				stdout=rebostHelper.getEpiStatus(data.get('episcript'))
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
				print(e)
				if isinstance(rebostpkg,dict):
					bundles=rebostpkg.get('bundle',"not found")
				else:
					self._debug(e)
			try:
				cats=json.loads(rebostpkg).get('categories',[])
			except Exception as e:
				print(e)
				if isinstance(rebostpkg,dict):
					cats=rebostpkg.get('categories',[])
				else:
					self._debug(e)
			forbidden=False
			if "Forbidden" in cats:
				rebostpkg=''
				rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'Forbidden {}, app unauthorized'.format(package)})]
				forbidden=True
				bundles=[]
			if len(bundles)>0:
				self.failProc+=1
				if not (bundle and bundle in bundles):
					if bundle:
						rebostpkg=''
						rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'not available as {}, only as {}'.format(bundle,"|".join(list(bundles.keys())))})]
					else:
						if len(bundles)>1:
							rebostpkg=''
							rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'available from many sources, please choose one from: {}'.format("|".join(list(bundles.keys())))})]
						else:
							bundle=list(bundles.keys())[0]
			elif forbidden==False:
				rebostpkg=''
				rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':package,'done':1,'status':'','msg':'not available as {}'.format(bundles)})]
		else:
			rebostpkg=''
			rebostPkgList=[("{}".format(self.failProc),{'pid':"{}".format(self.failProc),'package':pkgname,'done':1,'status':'','msg':'{0} for {1} not found'.format(bundle,pkgname)})]
		return(rebostpkg,bundle,rebostPkgList)
	#def _chk_pkg_format

	def _mpManagePackage(self,action,epifile,username,procQ):
		#self._debug("Starting process for {0} {1} as {2}".format(action,epifile,username))
		self._log("Starting process for {0} {1} as {2}".format(action,epifile,username))
		logDir=os.path.dirname(os.path.dirname(epifile))
		if os.path.isdir(logDir)==False:
			logDir="/tmp"
		logFile=os.path.join(logDir,"{}".format(os.path.basename(epifile).replace(".epi",".log")))
		self._log("Full process log at {}".format(logFile))
		if self.gui==True:
			return
			cmd=["/usr/share/rebost/helper/rebost-software-manager.sh",epifile]
		else:
			renv = os.environ.copy()
			if len(renv.get("USER",""))==0:
				renv["USER"]=username
			cmd=["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",epifile,"cli",action]
			#cmd=["/usr/sbin/epic",action,"-nc","-u",epifile]
			if action=="remove":
				cmd=["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",epifile,"cli","uninstall"]
			#	cmd=["/usr/bin/pkexec","epic","uninstall","-nc","-u",epifile]
		self._debug(" ".join(cmd))
		self._log(cmd)
		f=open(logFile,"w")
		proc=subprocess.Popen(cmd,stdout=f,universal_newlines=True,close_fds=True)
		self._debug(proc)
		procQ.put(proc.pid)
		while proc.poll()==None:
			print(".")
			time.sleep(0.01)
		self._debug(proc)
		self._debug("########################################################")
		f.close()
	#def _mpManagePackage

	def _remoteInstall(self,usern,episcript):
		sw=False
		apachePath="/var/www/llx-remote"
		scriptname=os.path.basename(episcript)
		if os.path.exists(apachePath)==True:
			destPath=os.path.join(apachePath,scriptname)
			shutil.copy(episcript,destPath)
			core=n4dcore.Core.get_core()
			remoteVar=core.get_variable("LLX_REMOTE_INSTALLER").get('return',{})
			if remoteVar:
				#Send file to apache dir as expected by remote-installer, then update remote-installer
				lines=subprocess.Popen(["LAGUAGE=en_EN; md5sum %s | awk '{print $1}'"%episcript],shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
				for line in lines.splitlines():
					md5=line.decode('utf-8')
				pkg_tupla=[episcript,md5]
				url='http://server/llx-remote/'
				if remoteVar.get('sh',[]):
					packages=remoteVar['sh'].get('packages',[])
					if packages==None:
						packages=[]
					packages.append((scriptname,md5))
					packagesSet=[]
					packagesAdded=[]
					for pkgtuple in packages:
						pkg=''
						if isinstance(pkgtuple,tuple):
							pkg,md5=pkgtuple
							if pkg not in packagesAdded:
								packagesAdded.append(pkg)
								packagesSet.append((pkg,md5))

					remoteVar['sh'].update({'packages':packagesSet})
				else:
					remoteVar.update({'sh':{'url':url,'packages':[scriptname]}})
				result=core.set_variable("LLX_REMOTE_INSTALLER",remoteVar)
				sw=True
		self._removeTempDir(episcript)
		if sw==False:
			self._debug("Remote installer not found")
		return(sw)
	#def _remoteInstall

	def _managePackage(self,pkgname,bundle='',action='install',user='',remote=False,n4dkey=''):
		self._debug("{} package {} as bundle {} for user {}".format(action,pkgname,bundle,user))
		#1st search that there's a package in the desired format
		(rebostpkg,bundle,rebostPkgList)=self._chk_pkg_format(pkgname,bundle)
		if rebostpkg:
		#Well, the package almost exists and the desired format is available so generate EPI files and return.
		#1st check if removing and if removing package doesn't removes meta
			sure=True
			if (action=='remove' or action=='test') and bundle=='package':
				jpkg={}
				try:
					jpkg=json.loads(rebostpkg)
				except:
					sure=False
				else:
					if jpkg.get("state",{}).get("package","1")=="0":
						if rebostHelper.chkUnsafeRemoval(pkgname):
							rebostPkgList=[("{}".format(self.failProc),
											{'pid':"{}".format(self.failProc),
											'package':pkgname,
											'done':1,
											'status':'',
											'msg':'package {} is a system package'.format(pkgname)})]
							sure=False
			if sure:
				usern="{}".format(user)
				postaction=""
				try:
					jpkg=json.loads(rebostpkg)
				except:
					jpkg={}
				if jpkg.get("bundle",{}).get("zomando","")!="":
					if (jpkg.get("state",{}).get("zomando","0")!="0") and ((jpkg.get("state",{}).get("package","0")!="0")):
						tmpAction="install"
						if bundle!="zomando":
							postaction="/usr/sbin/epic -u install {0}.epi 2>/dev/null || /usr/sbin/epic -u install zero-lliurex-{0}.epi".format(pkgname.replace("zero-lliurex-",""))
				(epifile,episcript)=rebostHelper.epiFromPkg(rebostpkg,bundle,user,remote,postaction)
				rebostPkgList=[(pkgname,{'package':pkgname,'status':action,'epi':epifile,'script':episcript,'bundle':bundle})]
				if action=="remote":
					self._remoteInstall(usern,episcript)
				elif action!="test":
					self._debug("Executing {0} query as user {1}".format(action,user))
					procQ=multiprocessing.Queue()
					#proc=threading.Thread(target=self._mpManagePackage,args=(action,epifile,usern,procQ,))
					proc=multiprocessing.Process(target=self._mpManagePackage,args=(action,epifile,usern,procQ,))
					proc.start()
					while procQ.empty():
						time.sleep(0.01)
					pid=procQ.get()
					rebostPkgList=[(pkgname,{'package':pkgname,'action':action,'status':action,'epi':epifile,'script':episcript,'pid':pid,'bundle':bundle})]
					self._insertProcess(rebostPkgList)
					#proc.terminate()
		return (rebostPkgList)
	#def _managePackage

	def _removeTempDir(self,tmpfile):
		tmpDir=os.path.dirname(tmpfile)
		if os.path.isdir(tmpDir):
			try:
				self._debug("Removing tmp dir {}".format(tmpDir))
				shutil.rmtree(tmpDir)
			except Exception as e:
				self._debug("Couldn't remove tmpdir {}: {}".format(tmpDir,e))
	#def _removeTempDir

def main():
	obj=rebostPrcMan()
	return (obj)
