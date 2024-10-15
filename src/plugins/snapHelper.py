#!/usr/bin/env python3
import os,shutil,stat
import gi
from gi.repository import Gio
gi.require_version ('Snapd', '2')
from gi.repository import Snapd
import json
import rebostHelper
import logging
import html2text
#from bs4 import BeautifulSoup
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class snapHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.packagekind="snap"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=2
		dbCache="/tmp/.cache/rebost"
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER"))
		if not os.path.exists(self.rebostCache):
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","sp.lu")
		self.snap=Snapd.Client()
		self.forceApps=["octoprint-sdev"]
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))

	def _debug(self,msg):
		if self.dbg:
			dbg="snap: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)

	def _loadStore(self):
		action="load"
		try:
			(rebostPkgList,update)=self._getSnapCatalogue()
		except Exception as e:
			raise
		if update:
			rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'snap.db')
			self._debug("SQL loaded")
		else:
			self._debug("Skip update")

	def _getSnapCatalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		update=False
		try:
			sections=self.snap.get_sections_sync()
		except Exception as e:
			self._debug(e)
		processed=[]
		for section in sections:
			try:
				apps,curr=self.snap.find_section_sync(Snapd.FindFlags.MATCH_NAME,section,None)
			except Exception as e:
				print(e)
				break
			if self._chkNeedUpdate(len(apps),section):
				updateFile=self.lastUpdate.replace("sp","sp_{}".format(section))
				with open(updateFile,'w') as f:
					f.write(str(len(apps)))
				update=True
				while apps:
					pkg=apps.pop(0)
					if pkg.get_name() not in processed:
						processed.append(pkg.get_name())
						rebostPkgList.append(self._process_snap_json(pkg,section))
		for snap in self.forceApps:
			searchsnap=self.snap.find_sync(Snapd.FindFlags.MATCH_NAME,snap,None)
			if searchsnap:
				pkg=searchsnap[0][0]
				if pkg.get_name() not in processed:
					processed.append(pkg.get_name())
					rebostPkgList.append(self._process_snap_json(pkg,section))
		return(rebostPkgList,update)

	def _chkNeedUpdate(self,lenApps,section):
		update=True
		appMd5=""
		lastUpdate=""
		updateFile=self.lastUpdate.replace("sp","sp_{}".format(section))
		if os.path.isfile(updateFile)==False:
			if os.path.isdir(os.path.dirname(updateFile))==False:
				os.makedirs(os.path.dirname(updateFile))
		else:
			fcontent=""
			with open(updateFile,'r') as f:
				lastUpdate=f.read()
			if str(lenApps)==lastUpdate:
				update=False
		return(update)
	#def _chkNeedUpdate

	def _process_snap_json(self,pkg,section):
		rebostPkg=rebostHelper.rebostPkg()
		rebostPkg['id']="io.snapcraft.{}".format(pkg.get_name())
		rebostPkg['name']=pkg.get_name()
		rebostPkg['pkgname']=pkg.get_name().lower()#.replace("_","-")
		rebostPkg['summary']=html2text.html2text(pkg.get_summary())
		rebostPkg['description']=html2text.html2text(pkg.get_description())
		#rebostPkg['categories']=['Snap']
		rebostPkg['kind']=5
		if pkg.get_icon():
			rebostPkg['icon']=pkg.get_icon()
		rebostPkg['versions']={"snap":"{}".format(pkg.get_version())}
		rebostPkg['size']={"snap":"{}".format(pkg.get_download_size())}
		if pkg.get_media():
			for media in pkg.get_media():
				rebostPkg['screenshots'].append(media.get_url())
		rebostPkg['homepage']="{}".format(pkg.get_website())
		if rebostPkg['homepage'].lower()=="none":
			rebostPkg['homepage']=""
		rebostPkg['license']="{}".format(pkg.get_license())
		state='1'
		if pkg.get_install_date():
			state='0'
		rebostPkg['state']={"snap":"{}".format(state)}
		rebostPkg['bundle'].update({'snap':"{}".format(pkg.get_name())})
		rebostPkg['categories']=self._get_categories(section)
		return rebostPkg

	def _get_categories(self,section):
		categories=[]
		catMap={
				"artanddesign":["Graphics","Art"],
				"art-and-design":["Graphics","Art"],
				"books-and-reference":["Documentation","Education"],
				"booksandreference":["Documentation","Education"],
				"development":["Development"],
				"devicesandiot":["Development","Robotics","Electronics"],
				"devices-and-lot":["Development","Robotics","Electronics"],
				"entertainment":["Amusement"],
				"education":["Education"],
				"finance":["Office","Finance"],
				"games":["Game"],
				"healthandfitness":["Utility","Amusement"],
				"health-and-fitness":["Utility","Amusement"],
				"musicandaudio":["AudioVideo"],
				"music-and-audio":["AudioVideo"],
				"newsandweather":["Network","News"],
				"news-and-weather":["Network","News"],
				"personalisation":["Settings"],
				"photoandvideo":["AudioVideo","Graphics"],
				"photo-and-video":["AudioVideo","Graphics"],
				"productivity":["Office"],
				"security":["System","Security"],
				"serverandcloud":["Network"],
				"server-and-cloud":["Network"],
				"science":["Science"],
				"social":["Network","InstantMessaging"],
				"utilities":["Utility"]
				}
		#Snap categories aren't standard so... 
		categories=catMap.get(section.lower().replace(" ",""),["Utility"])
		return(categories)

def main():
	obj=snapHelper()
	return (obj)

