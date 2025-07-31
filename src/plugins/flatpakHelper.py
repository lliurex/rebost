#!/usr/bin/env python3
import os,sys,stat,tempfile
import xml.etree.ElementTree as ET
import gi
from gi.repository import Gio
gi.require_version ('Flatpak', '1.0')
from gi.repository import Flatpak
gi.require_version('AppStreamGlib', '1.0')
from gi.repository import AppStreamGlib as appstream
import rebostHelper
import logging
import subprocess
import locale
localLangs=[locale.getdefaultlocale()[0].split("_")[0]]
localLangs.append("qcv")
if localLangs[0]=="ca":
	localLangs.append("es")
else:
	localLangs.append("ca")
localLangs.append("en")
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class flatpakHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self._debug("Loaded")
		self.enabled=True
		self.packagekind="flatpak"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=2
		dbCache="/tmp/.cache/rebost"
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER"))
		if os.path.exists(self.rebostCache)==False:
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.wrkDir=os.path.join(self.rebostCache,"xml","flatpak")
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","ft.lu")
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			dbg="flatpak: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			rs=self._loadStore()
		if action=='install':
			rs=["flatpak","--user","install"]
		return(rs)
	#def execute

	def _loadStore(self):
		action="load"
		self._debug("Get apps")
		store=self._getFlatpakCatalogue()
		update=self._chkNeedUpdate(store)
		rebostPkgList=[]
		if update:
			self._debug("Get rebostPkg")
			rebostPkgList=rebostHelper._appstreamToRebost(store)
			#Check state of packages
			installedRefs=self._getInstalledRefs()
			installed={}
			for i in installedRefs:
				installed[i.get_name().lower()]=i.get_appdata_version()
			upgradableRefs=self._getUpgradableRefs()
			upgradable={}
			for i in upgradableRefs:
				upgradable[i.get_name().lower()]=i.get_appdata_version()
				a=i.load_metadata()
			if len(installed)==0:
				rebostPkgList=self._fillInstalledData(rebostPkgList,installed)
			rebostHelper.rebostPkgsToSqlite(rebostPkgList,'flatpak.db')
			self._debug("SQL loaded")
			storeMd5=str(store.get_size())
			with open(self.lastUpdate,'w') as f:
				f.write(storeMd5)
		else:
			self._debug("Skip update")
		return(rebostPkgList)
	#def _loadStore(self):

	def _fillInstalledData(self,rebostPkgList,installed):
		for pkg in rebostPkgList:
			if pkg["id"] in installed:
				local=installed.pop(pkg["id"])
				if local==None:
					local="runtime"
				pkg["installed"].update({"flatpak":local})
				pkg["state"].update({"flatpak":"0"})
				if pkg["id"] in upgradable.keys():
					remote=upgradable.pop(pkg["id"])
					if remote==local and remote!=None:
						remote+="+1"
					elif remote==None:
						remote="runtime+1"
					pkg["versions"].update({"flatpak":remote})
		return(rebostPkgList)
	#def _fillInstalledData

	def _chkNeedUpdate(self,store):
		update=True
		lastUpdate=""
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
		else:
			fcontent=""
			with open(self.lastUpdate,'r') as f:
				lastUpdate=f.read()
			storeMd5=str(store.get_size())
			if storeMd5==lastUpdate:
				update=False
		return(update)
	#def _chkNeedUpdate
	
	def _updateMetadata(self,flInst,flRemote):
		self._debug("Updating metadata for {}".format(flRemote.get_name()))
		flInst.update_remote_sync(flRemote.get_name(),None)
		self._debug("Updating metadata from URL {}".format(flRemote.get_url()))
		flInst.prune_local_repo()
		flRemote.set_gpg_verify(False)
		flInst.modify_remote(flRemote,None)
		flInst.update_appstream_sync(flRemote.get_name(),None,None,None)
	#def _updateMetadata

	def _getFlatpakCatalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		progress=0
		flInst=''
		store=appstream.Store()
		tmpStore=appstream.Store()
		(srcDir,flInst)=self._getFlatpakMetadata()
		if srcDir=='':
		#When initializing for first time metada needs a reload
			(srcDir,flInst)=self._getFlatpakMetadata()
		flInst.set_config_sync("languages","{}".format(localLangs[0]))
		flInst.set_config_sync("extra-languages","{}".format(";".join(localLangs[1:])))
		self._debug("Loading flatpak metadata from file at {}".format(srcDir))
		fxml=os.path.join(srcDir,"appstream.xml")
		try:
			tmpStore.from_file(Gio.File.parse_name(fxml))
		except Exception as e:
			print("Flatpak BUG #5434 workaround")
			fcontent=self._fixAppstreamXml(fxml)
			tmpStore.from_file(Gio.File.parse_name(fcontent))
			#store.from_xml(fcontent)
		for app in tmpStore.get_apps():
			idx=app.get_id()
			icon=self._get_app_icons(srcDir,idx)
			if icon:
				app.add_icon(icon)
			store.add_app(app)
		self._debug("End loading flatpak metadata")
		return(store)
	#def _getFlatpakCatalogue

	def _fixAppstreamXml(self,fxml):
		fcontent=""
		tree = ET.parse(fxml)
		r=tree.getroot()
		for description in r.iter('description'):
			txt=[]
			for i in list(description):
				desc=i.text
				if isinstance(desc,str)==False:
					desc=""
				description.remove(i)
				txt.append(desc.strip())
			desc="<p>{}</p>".format(rebostHelper._sanitizeString(". ".join(txt),scape=True))
			try:
				elem=ET.fromstring(desc)
			except Exception as e:
				print(e)
				print(desc)
			description.append(elem)
		tmpfile=tempfile.mktemp()
		tree.write(tmpfile,xml_declaration="1.0",encoding="UTF-8")
		return tmpfile
	#def _fixAppstreamXml

	def _getFlatpakRemotes(self,flInst):
		remotes={}
		for installer in flInst:
			self._debug("Loading {}".format(installer))
			flRemote=installer.list_remotes()
			if len(flRemote)>0:
				remotes[installer]=flRemote
		return(remotes)
	#def _getFlatpakRemotes

	def _getFlatpakMetadata(self,systemInstall=False):
		#Get all the remotes, copy appstream to wrkdir
		flInst=[]
		flRemote=[]
		remotes=[]
		srcDir=''
		found=False
		if systemInstall==True:
			try:
				flInst=Flatpak.get_system_installations()
			except Exception as e:
				print("Error getting flatpak remote: {}".format(e))
			remotes=self._getFlatpakRemotes(flInst)
		if len(remotes)==0:
			self._debug("Reloading repo info")
			(flInst,flRemote)=self._init_flatpak_repo()
			remotes=self._getFlatpakRemotes([flInst])
		self._debug("Get REMOTES: {}".format(remotes))
		for installer,remotelist in remotes.items():
			for remote in remotelist:
				self._debug("Inspect {}".format(remote))
				srcDir=remote.get_appstream_dir().get_path()
				self._debug("flatpak srcdir: {}".format(srcDir))
				try:
					installer.update_appstream_sync(remote.get_name())
				except:
					self._debug("Error reaching remote {}".format(remote))
				self._debug("{} synced".format(srcDir))
		return(srcDir,flInst)
	#def _getFlatpakMetadata

	def _getInstalledRefs(self):
		flInst=None
		installedApps=[]
		try:
			flInst=Flatpak.get_system_installations()
		except Exception as e:
			print("Error getting flatpak remote: {}".format(e))
		if isinstance(flInst,list):
			for inst in flInst:
				installedApps.extend(inst.list_installed_refs())
		return(installedApps)
	#def _getInstalledRefs

	def _getUpgradableRefs(self):
		flInst=None
		upgradableApps=[]
		try:
			flInst=Flatpak.get_system_installations()
		except Exception as e:
			print("Error getting flatpak remote: {}".format(e))
		if isinstance(flInst,list):
			for inst in flInst:
				upgradableApps.extend(inst.list_installed_refs_for_update())
		return(upgradableApps)
	#def _getInstalledRefs

	def _get_state(self,flInst,pkg):
		state="available"
		for installer in flInst:
			installed=False
			fname=pkg.get_id_filename()
			flistName=fname.split("/")
			if len(flistName)>1:
				fname=fname.split("/")[1]
			try:
				#installed=installer.get_installed_ref(0,pkg.get_name())
				installed=installer.get_installed_ref(0,fname)
			except Exception as e:
				try:
					#installed=installer.get_installed_ref(1,pkg.get_name())
					installed=installer.get_installed_ref(1,fname)
				except Exception as e:
					pass
			if installed:
				state="installed"
				break
		return(state)
	#def _get_state

	def _get_app_icons(self,srcDir,idx):
		iconPath=''
		icon=None
		idx=idx.replace(".desktop","")
		iconDirs=[]
		baseDir=os.path.dirname(srcDir)
		for d in os.listdir(baseDir):
			f=os.path.join(baseDir,d,"icons")
			if os.path.isdir(f):
				iconDirs.append(f)
		for iconDir in iconDirs:

			icon64=os.path.join(iconDir,"64x64")
			icon128=os.path.join(iconDir,"128x128")
			if os.path.isfile(os.path.join(icon128,"{}.png".format(idx))):
				iconPath=os.path.join(icon128,"{}.png".format(idx))
				break
			elif os.path.isfile(os.path.join(icon64,"{}.png".format(idx))):
				iconPath=os.path.join(icon64,"{}.png".format(idx))
				break
		if iconPath!='':
			icon=appstream.Icon()
			icon.set_kind(appstream.IconKind.LOCAL)
			tmp=iconPath.split("/")
			idx=tmp.index("icons")
			if idx>0 and "flatpak" in iconPath:
				prefix=tmp[:idx-1]
				iconPath=os.path.join("/".join(prefix),"active","/".join(tmp[idx:]))
			icon.set_filename(iconPath)
		return(icon)
	#def _get_app_icons

	def _init_flatpak_repo(self):
		flInst=Flatpak.Installation.new_user(None)
		flRemote=Flatpak.Remote().new("flathub")
		flRemote.set_url('https://flathub.org/repo')#/flathub.flatpakrepo')
		flRemote.set_disabled(False)
		flInst.add_remote(flRemote,True,None)
		#cmd=['/usr/bin/flatpak','--user','remote-add','--if-not-exists','flathub','https://flathub.org/repo/flathub.flatpakrepo']
#		try:
#			subprocess.run(cmd)
#		except Exception as e:
#			print(e)
#			print("Flatpak source disabled")
		self._updateMetadata(flInst,flRemote)
		return(flInst,flRemote)
	#def _init_flatpak_repo

def main():
	obj=flatpakHelper()
	return (obj)

