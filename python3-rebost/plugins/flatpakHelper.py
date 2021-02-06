#!/usr/bin/env python3
import os
import shutil
import gi
from gi.repository import Gio
gi.require_version ('Flatpak', '1.0')
from gi.repository import Flatpak
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStream as appstream
import json
import definitions
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class flatpakHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		self.enabled=True
		self.packagekind="flatpak"
		self.actions=["load","install","remove"]
		self.autostartActions=["load"]
		self.priority=1
		self.store=None
		self.progressQ={}
		self.progress={}
		self.resultQ={}
		self.result={}
		self.wrkDir='/home/lliurex/.cache/rebost/xml/flatpak'
		#self.snap_client=Snapd.Client()
		#try:
	#		self.snap_client.connect_sync(None)
		#except Exception as e:
		#	self.enabled=True
		#	self._debug("Disabling snap %s"%e)

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			print("flatpak: %s"%str(msg))

	def _on_error(self,action,e):
		self.progressQ[action].put(100)
		self.resultQ[action].put(str(json.dumps([{'name':action,'description':'Error','error':"1",'errormsg':str(e)}])))


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

	def _loadStore(self):
		action="load"
		if not os.path.isdir(self.wrkDir):
			os.makedirs(self.wrkDir)
		rebostPkgList=self._get_flatpak_catalogue()
		self.progressQ[action].put(100)
		self.resultQ[action].put(str(json.dumps([{'name':'load','description':'Ready'}])))

	def _get_flatpak_catalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		progress=0
		inc=0
		flInst=''
		try:
			#Get all the remotes, copy appstream to wrkdir
			flInst=Flatpak.get_system_installations()
			for installer in flInst:
				flRemote=installer.list_remotes()
				for remote in flRemote:
					srcDir=remote.get_appstream_dir().get_path()
					installer.update_appstream_sync(remote.get_name())
					if os.path.exists(self.wrkDir):
						shutil.rmtree(self.wrkDir,ignore_errors=True)
					shutil.copytree(srcDir,self.wrkDir,symlinks=True)
			#sections=self.snap_client.get_sections_sync()
		except Exception as e:
			#print(e)
			#self._on_error("load",e)
			self.progressQ[action].put(progress)
		if os.path.isfile(os.path.join(self.wrkDir,"appstream.xml")):
			store=appstream.Pool()
			metadata=appstream.Metadata()
			store.clear_metadata_locations()
			store.add_metadata_location(self.wrkDir)
			try:
				store.load()
			except:
				pass
			added=[]
			for pkg in store.get_components():
				idx=pkg.get_id()
				idxList=idx.split(".")
				if len(idxList)>2:
					idxList[0]="org"
					idxList[1]="flathub"
					newId=".".join(idxList).lower()
				else:
					newId="org.flathub.{}".format(idx[-1])
				pkg.set_id(newId)
				state="available"
				for installer in flInst:
					installed=False
					try:
						installed=installer.get_installed_ref(0,pkg.get_name())
					except:
						try:
							installed=installer.get_installed_ref(1,pkg.get_name())
						except:
							pass
					if installed:
						state="installed"
						break
				add=False
				if not pkg.get_bundles():
					bundle=appstream.Bundle()
					bundle.set_id("{};amd64;{}".format(pkg.get_id(),state))
					bundle.set_kind(appstream.BundleKind.FLATPAK)
					pkg.add_bundle(bundle)
					add=True
				else:
					for bundle in pkg.get_bundles():
						bundle.set_id("{};amd64;{}".format(pkg.get_id(),state))
						bundle.set_kind(appstream.BundleKind.FLATPAK)
						add=True
				if add and pkg.get_id() not in added:
					metadata.add_component(pkg)
					added.append(pkg.get_id())
			os.remove(os.path.join(self.wrkDir,"appstream.xml"))
			metadata.save_collection(os.path.join(self.wrkDir,"appstream.xml"),appstream.FormatKind.XML)
			store.clear()
			metadata.clear_components()
		return(rebostPkgList)

	def _processRemote(self,installer,remote):
		for remoteRef in installer.list_remote_refs_sync_full(remote.get_name(),Flatpak.QueryFlags.NONE):
			flat=installer.get_remote_by_name(remoteRef.get_name())

	def _install(self,app_info):
		#self._debug("Installing %s"%app_info['name'])
		action="install"
		result=definitions.resultSet()
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
		result=definitions.resultSet()
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
	obj=flatpakHelper()
	return (obj)
