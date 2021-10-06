#!/usr/bin/env python3
import os
import gi
from gi.repository import Gio
gi.require_version ('Snapd', '1')
from gi.repository import Snapd
import json
import rebostHelper
import logging
from bs4 import BeautifulSoup
#Needed for async find method, perhaps only on xenial
wrap=Gio.SimpleAsyncResult()

class snapHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.packagekind="snap"
		self.actions=["load"]
		self.autostartActions=["load"]
		self.priority=1
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
			logging.warning("snap: %s"%str(msg))

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='load':
			self._loadStore()
		return(rs)

	def _loadStore(self):
		action="load"
		try:
			rebostPkgList=self._get_snap_catalogue()
		except Exception as e:
			raise
		rebostHelper.rebostPkgList_to_sqlite(rebostPkgList,'snap.db')
		
		self._debug("SQL loaded")

	def _get_snap_catalogue(self):
		action="load"
		rebostPkgList=[]
		sections=[]
		try:
			sections=self.snap_client.get_sections_sync()
		except Exception as e:
			self._debug(e)
		for section in sections:
			apps,curr=self.snap_client.find_section_sync(Snapd.FindFlags.MATCH_NAME,section,None)
			for pkg in apps:
				rebostPkg=self._process_snap_json(pkg,section)
				rebostPkgList.append(rebostPkg)
		return(rebostPkgList)

	def _process_snap_json(self,pkg,section):
		appinfo=rebostHelper.rebostPkg()
		appinfo['id']="io.snapcraft.{}".format(pkg.get_name().replace("-","_"))
		appinfo['name']=pkg.get_name()
		appinfo['pkgname']=pkg.get_name().lower().replace("_","-")
		appinfo['summary']=BeautifulSoup(pkg.get_summary(),"html.parser").get_text().replace("'","''")
		appinfo['description']=BeautifulSoup(pkg.get_description(),"html.parser").get_text().replace("'","''")
		#appinfo['categories']=['Snap']
		appinfo['kind']=5
		if pkg.get_icon():
			appinfo['icon']=pkg.get_icon()
		appinfo['versions']={"snap":"{}".format(pkg.get_version())}
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
			state='0'
			pkgs=[pkg]
		except:
			state='1'
		appinfo['state']={"snap":"{}".format(state)}
		#appinfo['bundle'].update({'snap':"{};amd64;{}".format(pkg.get_id(),state)})
		appinfo['bundle'].update({'snap':"{}".format(pkg.get_name())})
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

def main():
	obj=snapHelper()
	return (obj)

