#!/usr/bin/env python3
import sys
import subprocess
import zlib
import json
import time
import signal
import dbus,dbus.service,dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import rebostCore as rebost
import logging
import getpass

class rebostDbusMethods(dbus.service.Object):
	def __init__(self,bus_name,*args,**kwargs):
		super().__init__(bus_name,"/net/lliurex/rebost")
		logging.basicConfig(format='%(message)s')
		self.dbg=True
		self.rebost=rebost.Rebost()
		self.rebost.run()

	def _debug(self,msg):
		if self.dbg:
			logging.debug("rebost-dbus: %s"%str(msg))
			print("rebost-dbus: %s"%str(msg))

	def _print(self,msg):
		logging.info("rebost-dbus: %s"%str(msg))
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='b', out_signature='s')
	def enableGui(self,enable):
		ret=self.rebost._setGuiEnabled(enable)
		return (str(ret))

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssss', out_signature='s')
	def install(self,pkg,bundle,user='',n4dkey=''):
		action='install'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user,n4dkey=n4dkey)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='sss', out_signature='s')
	def test(self,pkg,bundle,user=''):
		action='test'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssss', out_signature='s')
	def remote_install(self,pkg,bundle,user='',n4dkey=''):
		action='remote'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user,n4dkey=n4dkey)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='i')
	def load(self):
		action='load'
		ret=self.rebost.execute(action)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getCategories(self):
		action='getCategories'
		ret=self.rebost.execute(action)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='ay')
	def search(self,pkgname):
		action='search'
		pkgname=pkgname.lower()
		ret=self.rebost.execute(action,pkgname)
		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='ay')
	def search_by_category(self,category):
		action='list'
		ret=self.rebost.execute(action,category)
		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='si', out_signature='ay')
	def search_by_category_limit(self,category,limit):
		action='list'
		ret=self.rebost.execute(action,category,limit)
		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def show(self,pkg,user=''):
		action='show'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,user)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssss', out_signature='s')
	def remove(self,pkg,bundle,user='',n4dkey=''):
		action='remove'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user,n4dkey=n4dkey)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='sss', out_signature='s')
	def commitInstall(self,args,bundle,state):
		action='commitInstall'
		ret=self.rebost.execute(action,args,bundle,state)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def addTransaction(self,args):
		action='insert'
		ret=self.rebost.execute(action,args)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def getEpiPkgStatus(self,epifile):
		ret=self.rebost.getEpiPkgStatus(epifile)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getResults(self):
		ret=self.rebost.getProgress()
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getInstalledApps(self):
		action='list'
		ret=self.rebost.execute(action,installed=True)
#		ret = zlib.compress(ret.encode(),level=1)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getUpgradableApps(self):
		action='list'
		ret=self.rebost.execute(action,installed=True,upgradable=True)
		data=json.loads(ret)
		filterData=[]
		for strpkg in data:
			pkg=json.loads(strpkg)
			states=pkg.get('state',{})
			installed=pkg.get('installed',{})
			if isinstance(installed,str):
				installed={}
			versions=pkg.get('versions',{})
			for bundle,state in states.items():
				if state=="0":
					installed=installed.get(bundle,0)
					if ((installed!=versions.get(bundle,0)) and (installed!=0)):
						filterData.append(strpkg)
		ret=json.dumps(filterData)
		return (ret)
	#def getUpgradableApps(self):
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='b', out_signature='ay')
	def update(self,force=False):
		self.rebost.forceUpdate(force)
		ret=self.restart()

#		ret = zlib.compress(ret.encode(),level=1)
		return ()

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def restart(self):
		ret=True
		self.rebost=None
		self.rebost=rebost.Rebost()
		try:
			self.rebost.run()
		except:
			ret=False
#		ret = zlib.compress(ret.encode(),level=1)
		return (ret)

	def getPlugins(self):
		pass
	

class rebostDBus():
	
	def __init__(self): 
		self._setDbus()

	def _setDbus(self):
		DBusGMainLoop(set_as_default=True)
		loop = GLib.MainLoop()
		# Declare a name where our service can be reached
		try:
			bus_name = dbus.service.BusName("net.lliurex.rebost",
											bus=dbus.SystemBus(),
											do_not_queue=True)
		except dbus.exceptions.NameExistsException:
			print("service is already running")
			sys.exit(1)

		rebostDbusMethods(bus_name)
		# Run the loop
		try:
			loop.run()
		except KeyboardInterrupt:
			print("keyboard interrupt received")
		except Exception as e:
			print("Unexpected exception occurred: '{}'".format(str(e)))
		finally:
			loop.quit()

rebostDBus()
