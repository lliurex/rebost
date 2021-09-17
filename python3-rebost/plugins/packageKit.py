#!/usr/bin/env python3
import gi
gi.require_version('PackageKitGlib', '1.0')
from gi.repository import PackageKitGlib as packagekit
import threading
import time
import json
import threading
import rebostHelper
import logging
import html
from queue import Queue

class packageKit():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self._debug("Loaded")
		self.packagekind="package"
		self.actions=["load","install","remove"]
		self.autostartActions=["load"]
		self.priority=0
		self.progress={}
		self.progressQ={}
		self.resultQ={}
		self.queue=Queue(maxsize=0)
		self.result=''
		self.wrkDir="/tmp/.cache/rebost/xml/packageKit"
		#self.pkcon=None
		self.pkcon=packagekit.Client()
#		self._loadStore()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("packagekit: %s"%str(msg))

	def execute2(self,action,*args):
		rs=''
		if not self.pkcon:
			self.pkcon=packagekit.Client()
		if action=='search':
			rs=self._searchPackage(*args)
		if action=='show':
			rs=self._showPackage(*args)
		return(rs)

	def execute(self,procId,action,progress,result,store=None,args=''):
		if action in self.actions:
			self.progressQ[action]=progress
			self.resultQ[action]=result
			self.progress[action]=0
			if not self.pkcon:
				self.pkcon=packagekit.Client()
			self.progress[action]=0
			if action=='load':
				self._loadStore()
			if action=='install':
				self._install(args)
			if action=='remove':
				self._remove(args)
			if action=='info':
				self._info(args)

	def getStatus(self):
		return (self.progress)

	def _searchPackage(self,package):
		action='search'
		filters=1
		searchResults=[]
		pkilst=[]
		try:
			pklist=self.pkcon.search_details(filters,[package],None,self._search_callback,None)
		except Exception as e:
			print("PackageKit error; %s"%e)
		searchResults=self._collectSearchInfo(pklist)
		return(searchResults)
	
	def _showPackage(self,package):
		action='show'
		filters=1
		searchResults=[]
		pkilst=[]
		try:
			pklist=self.pkcon.resolve(filters,[package],None,self._search_callback,None)
		except Exception as e:
			print("PackageKit error; %s"%e)
		searchResults=self._collectSearchInfo(pklist)
		return(searchResults)

	def _info(self,rebostPkg):
		self.progressQ[action].put(100)
		self.resultQ[action].put(str(json.dumps([rebostPkg])))

	def _collectSearchInfo(self,pklist):
		action='search'
		searchResults=[]
		added=[]
		for pkg in pklist.get_package_array():
			if pkg.get_name() in added:
				continue
			#rs=definitions.resultSet()
			rebostpkg=rebostHelper.rebostPkg()
			rebostpkg['name']=pkg.get_name()
			rebostpkg['pkgname']=pkg.get_name()
			rebostpkg['id']="org.packagekit.%s"%pkg.get_name()
			rebostpkg['summary']=pkg.get_summary()
			rebostpkg['description']=pkg.get_summary()
			rebostpkg['version']="package-{}".format(pkg.get_version())
			rebostpkg['bundle']={"package":"{}".format(pkg.get_id())}
			searchResults.append(rebostpkg)
			#searchResults.append(pkg)
		return(searchResults)

	def _search_callback(self,*args):
		action='search'
		#progress=self.progress[action]
		#if args[0].get_percentage()>=100 and progress==100:
		#   args[0].set_percentage(100)
		#else:
		#   args[0].set_percentage(args[0].get_percentage()+10)
		#progress=args[0].get_percentage()
		#self.progress[action]=self.progress[action]+progress
		#self.progressQ[action].put(int(self.progress[action]/8.33))

	def _install(self,package):
		action="install"
		searchResults=[]
		filters=1
		pklist=self.pkcon.search_names(filters,[package['name']],None,self._install_callback,None)
		pkg=None
		resultSet=definitions.resultSet()
		for pk in pklist.get_package_array():
			if package['name']==pk.get_name():
				pkg=pk
				break
		if pkg:
			resultSet['name']=pkg.get_name()
			resultSet['pkgname']=pkg.get_name()
			resultSet['id']=pkg.get_id()
			self._debug("Installing %s"%pkg.get_id())
			err=0
			try:
				self.pkcon.install_packages(True,[pkg.get_id(),],None,self._install_callback,None)
				resultSet['description']='Installed'
				resultSet['error']=0
			except Exception as e:
				resultSet['errormsg']=str(e)
				resultSet['error']=1
		else:
			resultSet['errormsg']="Package %s not found"%package['name']
			resultSet['error']=2
		searchResults.append(resultSet)
		self.resultQ[action].put(str(json.dumps(searchResults)))
		self.progressQ[action].put(100)
	
	def _install_callback(self,*args):
		action='install'
		if action not in self.progress.keys():
			action='remove'
		progress=self.progress[action]
		if type(args[0])==type(0):
			self.progress[action]=0
			self.progressQ[action].put(0)
			return
		if args[0].get_percentage()>=100 and progress==100:
			args[0].set_percentage(100)
		else:
			args[0].set_percentage(args[0].get_percentage()+10)
		progress=args[0].get_percentage()
		self.progress[action]=self.progress[action]+progress
		if not self.progressQ[action].empty():
			while not self.progressQ[action].empty():
				self.progressQ[action].get()
		if self.progress[action]>=833:
			self.progress[action]=700
		self.progressQ[action].put(int(self.progress[action]/8.33))


	def _remove(self,package):
		action='remove'
		searchResults=[]
		filters=1
		pklist=self.pkcon.search_names(filters,[package['name']],None,self._install_callback,None)
		pkg=None
		resultSet=definitions.resultSet()
		for pk in pklist.get_package_array():
			if package['name']==pk.get_name():
				pkg=pk
				break
		if pkg:
			resultSet['name']=pkg.get_name()
			resultSet['pkgname']=pkg.get_name()
			resultSet['id']=pkg.get_id()
			try:
				self.pkcon.remove_packages(True,[pkg.get_id(),],True,False,None,self._install_callback,None)
			except Exception as e:
				self._debug("Remove error: %s"%e)
				resultSet['error']=1
				resultSet['errormsg']=str(e)
		searchResults.append(resultSet)
		self.resultQ[action].put(str(json.dumps(searchResults)))
		self.progressQ[action].put(100)
	#def _remove

	def _loadStore(self,*args):
		action="load"
		self._debug("Getting pkg list")
		pkgList=self.pkcon.get_packages(packagekit.FilterEnum.NONE, None, self._load_callback, None)
		self._debug("End Getting pkg list")
		rebostPkgList=[]
		added=[]
		semaphore = threading.BoundedSemaphore(value=10)
		thList=[]
		for pkg in pkgList.get_package_array():
			if pkg.get_name() in added or pkg.get_arch() not in ['amd64','all']:
				continue
			th=threading.Thread(target=self._th_generateXml,args=(pkg,semaphore,))
			th.start()
			thList.append(th)
		for th in thList:
			th.join()
		self._debug("PKG loaded")
		pkgList=[]
		while not self.queue.empty():
			pkgList.append(self.queue.get())
		rebostHelper.rebostPkgList_to_sqlite(pkgList,'packagekit.db')
		self._debug("SQL loaded")
		self.progressQ[action].put(100)
	
	def _th_generateXml(self,pkg,semaphore):
		semaphore.acquire()
		if pkg.get_arch() not in ['amd64','all']:
			semaphore.release()
			return

		rebostPkg=rebostHelper.rebostPkg()
		rebostPkg['name']=pkg.get_name()
		rebostPkg['pkgname']=pkg.get_name()
		rebostPkg['id']="org.packagekit.%s"%pkg.get_name()
		rebostPkg['summary']=html.escape(pkg.get_summary()).encode('ascii', 'xmlcharrefreplace').decode() 
		rebostPkg['description']=html.escape(pkg.get_summary()).encode('ascii', 'xmlcharrefreplace').decode() 
		rebostPkg['version']="package-{}".format(pkg.get_version())
		rebostPkg['bundle']={"package":"{}".format(pkg.get_id())}
		self.queue.put(rebostPkg)
		semaphore.release()

	def _load_callback(self,*args):
		#action='install'
		action='load'
		#return
		progress=self.progress.get(action,0)
		if type(args[0])==type(0):
			self.progress[action]=0
			self.progressQ[action].put(0)
			return
		if args[0].get_percentage()>=100 and progress==100:
			args[0].set_percentage(100)
		else:
			args[0].set_percentage(args[0].get_percentage()+10)
		progress=args[0].get_percentage()
		self.progressQ[action].put(int(self.progress.get(action,0)/8.33))

def main():
	obj=packageKit()
	return(obj)

