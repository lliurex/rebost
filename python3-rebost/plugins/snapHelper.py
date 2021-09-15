#!/usr/bin/env python3
import os
import gi
from gi.repository import Gio
gi.require_version ('Snapd', '1')
from gi.repository import Snapd
import json
import rebostHelper
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class snapHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.enabled=True
		self.packagekind="snap"
		self.actions=["show","search","load","install","remove"]
#		self.autostartActions=["load"]
		self.priority=1
		self.store=None
		self.progressQ={}
		self.progress={}
		self.resultQ={}
		self.result={}
		self.wrkDir='/tmp/.cache/rebost/xml/snap'
		self.snap_client=Snapd.Client()
		try:
			self.snap_client.connect_sync(None)
		except Exception as e:
			self.enabled=True
			self._debug("Disabling snap %s"%e)

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			print("snap: %s"%str(msg))

	def _on_error(self,action,e):
		self.progressQ[action].put(100)
		self.resultQ[action].put(str(json.dumps([{'name':action,'description':'Error','error':"1",'errormsg':str(e)}])))

#	def execute(self,action,*args):
#		rs=''
#		if action=='search':
#			rs=self._searchPackage(*args)
#		if action=='show':
#			rs=self._showPackage(*args)
#		return(rs)

	def execute(self,procId,action,progress,result,store,args=''):
		self.procId=procId
		if action in self.actions:
			self.progressQ[action]=progress
			self.resultQ[action]=result
			self.progress[action]=0
			if action=='load':
				self._loadStore()
			if action=='install':
				self._install(args)
			if action=='remove':
				self._remove(args)
	
	def _showPackage(self,package):
		#self._debug("Searching %s"%tokens)
		pklist=None
		package=package.replace("_","-")
		try:
			pklist,curr=self.snap_client.find_sync(Snapd.FindFlags.MATCH_NAME,package,None)
		except Exception as e:
			print("ERR: %s"%e)
			#self._set_status(1)
####	stable_pkgs=[]
####	for pkg in pkgs:
####		if force_stable:
####			if pkg.get_channel()=='stable':
####				stable_pkgs.append(pkg)
####			else:
####				#self._debug(pkg.get_channel())
####				pass
####		else:
####			stable_pkgs.append(pkg)
		#self._debug("Done")
		searchResults=self._collectSearchInfo(pklist)
		return(searchResults)

	def _searchPackage(self,package):
		#self._debug("Searching %s"%tokens)
		pklist=None
		package=package.replace("_","-")
		try:
			pklist,curr=self.snap_client.find_sync(Snapd.FindFlags.NONE,package,None)
		except Exception as e:
			print("ERR: %s"%e)
			#self._set_status(1)
####	stable_pkgs=[]
####	for pkg in pkgs:
####		if force_stable:
####			if pkg.get_channel()=='stable':
####				stable_pkgs.append(pkg)
####			else:
####				#self._debug(pkg.get_channel())
####				pass
####		else:
####			stable_pkgs.append(pkg)
		#self._debug("Done")
		searchResults=self._collectSearchInfo(pklist)
		return(searchResults)

	def _collectSearchInfo(self,pklist=[]):
		action='search'
		searchResults=[]
		added=[]
		if pklist:
			for pkg in pklist:
				if pkg.get_name() in added:
					continue
				rebostpkg=rebostHelper.rebostPkg()
				rebostpkg['id']="io.snapcraft.{}".format(pkg.get_name().replace("-","_"))
				rebostpkg['name']=pkg.get_name()
				rebostpkg['pkgname']=pkg.get_name().lower().replace("_","-")
				rebostpkg['summary']=pkg.get_summary()
				rebostpkg['description']=pkg.get_description()
				#rebostpkg['categories']=['Snap']
				rebostpkg['kind']=5
				if pkg.get_icon():
					rebostpkg['icon']=pkg.get_icon()
				rebostpkg['version']="snap-{}".format(pkg.get_version())
				#if pkg.get_screenshots():
				#if 'screenshots' in appimage.keys():
				#	appinfo['thumbnails']=appimage['screenshots']
				#if 'links' in appimage.keys():
				#	if appimage['links']:
				#		for link in appimage['links']:
				#			if 'url' in link.keys() and link['type']=='Download':
				#				appinfo['installerUrl']=link['url']
				#if 'authors' in appimage.keys():
				#	if appimage['authors']:
				#		for author in appimage['authors']:
				#			if 'url' in author.keys():
				#				#self._debug("Author: %s"%author['url'])
				#				appinfo['homepage']=author['url']
				state="available"
				try:
					pkg=self.snap_client.list_one_sync(pkg.get_name())
					state='installed'
					pkgs=[pkg]
				except:
					state='available'
				rebostpkg['bundle'].update({'snap':"{};amd64;{}".format(pkg.get_id(),state)})
				#rebostpkg['categories']=self._get_categories(section)
				searchResults.append(rebostpkg)
				#searchResults.append(pkg)
		return(searchResults)

	def _loadStore(self):
		action="load"
		try:
			rebostPkgList=self._get_snap_catalogue()
		except Exception as e:
			raise
		rebostHelper.rebostPkgList_to_xml(rebostPkgList,'/tmp/.cache/rebost/xml/snap/snap.xml')
		
		self.progressQ[action].put(100)
		self.resultQ[action].put(str(json.dumps([{'name':'load','description':'Ready'}])))

	def _get_snap_catalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		progress=0
		try:
			sections=self.snap_client.get_sections_sync()
		except Exception as e:
			self._on_error("load",e)
		inc=100.0/(len(sections)+1)
		for section in sections:
			apps,curr=self.snap_client.find_section_sync(Snapd.FindFlags.MATCH_NAME,section,None)
			for pkg in apps:
				rebostPkg=self._process_snap_json(pkg,section)
				rebostPkgList.append(rebostPkg)
			progress+=inc
			self.progressQ[action].put(progress)
		return(rebostPkgList)

	def _process_snap_json(self,pkg,section):
		appinfo=rebostHelper.rebostPkg()
		appinfo['id']="io.snapcraft.{}".format(pkg.get_name().replace("-","_"))
		appinfo['name']=pkg.get_name()
		appinfo['pkgname']=pkg.get_name().lower().replace("_","-")
		appinfo['summary']=pkg.get_summary()
		appinfo['description']=pkg.get_description()
		#appinfo['categories']=['Snap']
		appinfo['kind']=5
		if pkg.get_icon():
			appinfo['icon']=pkg.get_icon()
		appinfo['version']="snap-{}".format(pkg.get_version())
		#if pkg.get_screenshots():
		#if 'screenshots' in appimage.keys():
		#	appinfo['thumbnails']=appimage['screenshots']
		#if 'links' in appimage.keys():
		#	if appimage['links']:
		#		for link in appimage['links']:
		#			if 'url' in link.keys() and link['type']=='Download':
		#				appinfo['installerUrl']=link['url']
		#if 'authors' in appimage.keys():
		#	if appimage['authors']:
		#		for author in appimage['authors']:
		#			if 'url' in author.keys():
		#				#self._debug("Author: %s"%author['url'])
		#				appinfo['homepage']=author['url']
		state="available"
		try:
			pkg=self.snap_client.list_one_sync(pkg.get_name())
			state='installed'
			pkgs=[pkg]
		except:
			state='available'
		appinfo['bundle'].update({'snap':"{};amd64;{}".format(pkg.get_id(),state)})
		appinfo['categories']=self._get_categories(section)
		return appinfo	

	def _get_categories(self,section):
		categories=[]
		catMap={"development":["Development"],
				"games":["Game"],
				"social":["Network","InstantMessaging"],
				"productivity":["Office"],
				"utilities":["Utility"],
				"photoandvideo":["AudioVideo","Graphics"],
				"serverandcloud":["Network"],
				"security":["System","Security"],
				"devicesandlot":["Development","Robotics","Electronics"],
				"musicandaudio":["AudioVideo"],
				"entertainment":["Amusement"],
				"artanddesign":["Graphics","Art"],
				"booksandreference":["Documentation","Education"],
				"education":["Education"],
				"finance":["Office","Finance"],
				"healthandfidness":["Utility","Amusement"],
				"newsandweather":["Network","News"],
				"personalisation":["Settings"],
				"science":["Science"]
				}
		#Snap categories aren't standard so... 
		categories=catMap.get(section.lower().replace(" ",""),["Utility"])
		return(categories)

	
	def _install(self,app_info):
		#self._debug("Installing %s"%app_info['name'])
		action="install"
		result=rebostHelper.resultSet()
		result['id']=self.procId
		result['name']=action
		result['description']='%s'%app_info['pkgname']
		def install(app_name,flags):
			self.snap_client.install2_sync(flags,app_name.replace('.snap',''),
					None, # channel
					None, #revision
					self._callback, (None,),
					None) # cancellable
			result['msg']='installed'

		#if app_info['state']=='installed':
		#	self._set_status(4)
		#else:
		try:
			install(app_info['name'],Snapd.InstallFlags.NONE)
		except Exception as e:
				#try:
					#	if e.code==19:
					#install(app_info['name'],Snapd.InstallFlags.CLASSIC)
			#except Exception as e:
				self._debug("Install error %s"%e)
				result['msg']='error: %s'%e
				result['errormsg']='error: %s'%e
				result['error']=1
		#self._debug("Installed %s"%app_info)
		self.resultQ[action].put(str(json.dumps([result])))
		self.progress[action] = 100
		self.progressQ[action].put(int(self.progress[action]))
		return app_info
	#def _install_snap
		
	def _callback(self,client,change, _,user_data):
	    # Interate over tasks to determine the aggregate tasks for completion.
		action='install'
		if action not in self.progress.keys():
			action='remove'
			
		total = 0
		done = 0
		for task in change.get_tasks():
			total += task.get_progress_total()
			done += task.get_progress_done()
		acum=round((done/total)*100)
		if acum>self.progress[action]:
			self.progress[action]=acum
		if not self.progressQ[action].empty():
			while not self.progressQ[action].empty():
				self.progressQ[action].get()

		self.progressQ[action].put(int(self.progress[action]))
	#def _callback

	def _remove(self,app_info):
		action='remove'
		result=rebostHelper.resultSet()
		result['id']=self.procId
		result['name']=action
		result['description']='%s'%app_info['pkgname']
			#		if app_info['state']=='available':
#			self._set_status(3)
			#pass
		#else:
		try:
			self.snap_client.remove_sync(app_info['name'].replace('.snap',''),
                   self._callback, (None,),
					None) # cancellable
			#	app_info['state']='available'
#			self._set_status(0)
		except Exception as e:
				print("Remove error %s"%e)
#				self._set_status(6)
		self.resultQ[action].put(str(json.dumps([result])))
		self.progress[action] = 100
		self.progressQ[action].put(int(self.progress[action]))
	#def _remove_snap
def main():
	obj=snapHelper()
	return (obj)
