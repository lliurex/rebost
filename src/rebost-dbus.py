#!/usr/bin/env python3
import sys
import zlib
import json
import signal
import dbus,dbus.service,dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import rebostCore as rebost
import logging

class rebostDbusMethods(dbus.service.Object):
	def __init__(self,bus_name,*args,**kwargs):
		super().__init__(bus_name,"/net/lliurex/rebost")
		logging.basicConfig(format='%(message)s')
		self.dbg=kwargs["dbg"]
		signal.signal(signal.SIGUSR2, self._reloadSignal)
		signal.signal(signal.SIGUSR1, self._updatedSignal)
		signal.signal(signal.SIGALRM, self._beginUpdateSignal)
		self.rebost=rebost.Rebost()
		self.rebost.run()
	#def __init__

	def _debug(self,msg):
		if self.dbg:
			logging.debug("rebost-dbus: %s"%str(msg))
			print("rebost-dbus: %s"%str(msg))
	#def _debug

	def _beginUpdateSignal(self,*args,**kwargs):
		self.beginUpdateSignal()
	#def _beginUpdateSignal

	def _reloadSignal(self,*args,**kwargs):
		self.reloadSignal()
	#def _reloadSignal

	def _updatedSignal(self,*args,**kwargs):
		self.updatedSignal()
	#def _updatedSignal

	def _print(self,msg):
		logging.info("rebost-dbus: %s"%str(msg))
	#def _print

	@dbus.service.signal("net.lliurex.rebost")
	def loaded(self):
		pass

	@dbus.service.signal("net.lliurex.rebost")
	def beginUpdateSignal(self):
		pass
	#def storeLoaded

	@dbus.service.signal("net.lliurex.rebost")
	def reloadSignal(self):
		pass
	#def storeLoaded

	@dbus.service.signal("net.lliurex.rebost")
	def updatedSignal(self):
		pass
	#def storeUpdated
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='b', out_signature='s')
	def enableGui(self,enable):
		ret=self.rebost._setGuiEnabled(enable)
		return (str(ret))
	#def enableGui

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssss', out_signature='s')
	def install(self,pkg,bundle,user='',n4dkey=''):
		action='install'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user,n4dkey=n4dkey)
		return (ret)
	#def install

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='sss', out_signature='s')
	def test(self,pkg,bundle,user=''):
		action='test'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user)
		return (ret)
	#def test
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssss', out_signature='s')
	def remote_install(self,pkg,bundle,user='',n4dkey=''):
		action='remote'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user,n4dkey=n4dkey)
		return (ret)
	#def remote_install

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def load(self):
		action='load'
		ret=self.rebost.execute(action)
		return (ret)
	#def load

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getCategories(self):
		action='getCategories'
		ret=self.rebost.execute(action)
		return (ret)
	#def getCategories

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getFreedesktopCategories(self):
		action='getFreedesktopCategories'
		ret=self.rebost.execute(action)
		return (ret)
	#def getCategories

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='ay')
	def search(self,pkgname):
		action='search'
		pkgname=pkgname.lower()
		ret=self.rebost.execute(action,pkgname)
		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	#def search
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='ay')
	def search_by_category(self,category):
		action='list'
		ret=self.rebost.execute(action,category)
		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	#def search_by_category
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='si', out_signature='ay')
	def search_by_category_limit(self,category,limit):
		action='list'
		ret=self.rebost.execute(action,category,limit)
		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	#def search_by_category_limit
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def export(self,user=''):
		action='export'
		ret=self.rebost.execute(action,user)
		return (ret)
	#def export

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def match(self,pkg,user=''):
		action='match'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,user)
		return (ret)
	#def match

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def show(self,pkg,user=''):
		action='show'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,user)
		return (ret)
	#def show
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ssss', out_signature='s')
	def remove(self,pkg,bundle,user='',n4dkey=''):
		action='remove'
		pkg=pkg.lower()
		ret=self.rebost.execute(action,pkg,bundle,user=user,n4dkey=n4dkey)
		return (ret)
	#def remove
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='sss', out_signature='s')
	def commitInstall(self,args,bundle,state):
		action='commitInstall'
		ret=self.rebost.execute(action,args,bundle,state)
		return (ret)
	#def commitInstall

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def updatePkgData(self,args,data):
		action='updatePkgData'
		ret=self.rebost.execute(action,args,data)
		return (ret)
	#def commitInstall
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def addTransaction(self,args):
		action='insert'
		ret=self.rebost.execute(action,args)
		return (ret)
	#def addTransaction
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def getEpiPkgStatus(self,epifile):
		ret=self.rebost.getEpiPkgStatus(epifile)
		return (ret)
	#def getEpiPkgStatus
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getResults(self):
		ret=self.rebost.getProgress()
		return (ret)
	#def getResults
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='s')
	def getInstalledApps(self):
		action='list'
		ret=self.rebost.execute(action,installed=True)
#		ret = zlib.compress(ret.encode(),level=1)
		return (ret)
	#def getInstalledApps

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='s', out_signature='s')
	def getUpgradableApps(self,user=""):
		action='list'
		ret=self.rebost.execute(action,installed=True,upgradable=True,user=user)
		return (ret)
	#def getUpgradableApps(self):
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='b', out_signature='b')
	def update(self,force=False):
		ret=True
		#self.beginUpdateSignal()
		try:
			self.rebost.forceUpdate(force)
		except:
			ret=False
#		ret = zlib.compress(ret.encode(),level=1)
		return ret
	#def update

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def restart(self):
		ret=True
		try:
			self.rebost.execute("restart")
		except Exception as e:
			print("Critical error relaunching")
			print(str(e))
			ret=False
		return (ret)
	#def restart(self):

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def lock(self):
		ret=False
		try:
			ret=self.rebost.execute("lock")
		except Exception as e:
			print("Critical error locking")
			print(str(e))
		return(ret)
	#def lock

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def unlock(self):
		ret=False
		try:
			ret=self.rebost.execute("unlock")
		except Exception as e:
			print("Critical error unlocking")
			print(str(e))
		return(ret)
	#def unlock

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='b')
	def getLockStatus(self):
		ret=False
		try:
			ret=self.rebost.getLockStatus()
		except Exception as e:
			print("Critical error getting lock status")
			print(str(e))
		return(ret)
	#def getLockStatus

	#@dbus.service.method("net.lliurex.rebost",
	#					 in_signature='', out_signature='')
	#def disableFilters(self):
	#	try:
	#		self.rebost.execute("disableFilters")
	#	except Exception as e:
	#		print("Critical error disabling filters")
	#		print(str(e))
	##def disableFilters

	#@dbus.service.method("net.lliurex.rebost",
	#					 in_signature='', out_signature='b')
	#def getFiltersEnabled(self):
	#	ret=True
	#	try:
	#		ret=self.rebost.getFiltersEnabled()
	#	except Exception as e:
	#		print("Critical error reading filters")
	#		print(str(e))
	#	return(ret)
	##def disableFilters

	def getPlugins(self):
		pass

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='')
	def commitData(self):
		ret=self.rebost.commitData()
#		ret = zlib.compress(ret.encode(),level=1)
	#def commitData

#class rebostDbusMethods
	

class rebostDBus():
	def __init__(self): 
		self.dbg=False
		if len(sys.argv)>1:
			if sys.argv[0]=="-d":
				self.dbg=True
		self._setDbus()
	#def __init__

	def _setDbus(self):
		DBusGMainLoop(set_as_default=True)
		loop = GLib.MainLoop()
		# Declare a name where our service can be reached
		try:
			bus_name = dbus.service.BusName("net.lliurex.rebost",
											bus=dbus.Bus(),
											do_not_queue=True)
		except dbus.exceptions.NameExistsException:
			print("service is already running")
			sys.exit(1)

		rebostDbusMethods(bus_name,dbg=self.dbg)
		# Run the loop
		try:
			loop.run()
		except KeyboardInterrupt:
			print("keyboard interrupt received")
		except Exception as e:
			print("Unexpected exception occurred: '{}'".format(str(e)))
		finally:
			loop.quit()
	#def _setDbus
#class rebostDBus

rebostDBus()
