#!/usr/bin/env python3
import sys
import time
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
		self.dbg=True
		self.rebost=rebost.Rebost()
		self.rebost.run()

	def _debug(self,msg):
		if self.dbg:
			logging.warning("rebost-dbus: %s"%str(msg))
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='b', out_signature='s')
	def enableGui(self,args):
		ret=self.rebost._setGuiEnabled(args)
		return ("")

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def install(self,args,extraParms):
		action='install'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='i')
	def load(self,args,extraParms):
		action='load'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def search(self,args,extraParms=''):
		action='search'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='i')
	def listAll(self,args,extraParms):
		action='list'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='i')
	def search_by_category(self,args,extraParms):
		action='list'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def show(self,args,extraParms):
		action='show'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='s')
	def remove(self,args,extraParms):
		action='remove'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='sss', out_signature='s')
	def commitInstall(self,args,bundle,state):
		action='commitInstall'
		ret=self.rebost.execute(action,args,bundle,state)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='i')
	def update(self):
		action='update'
		ret=self.rebost.update()
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='', out_signature='i')
	def fullUpdate(self):
		action='update'
		ret=self.rebost.fullUpdate()
		ret=self.rebost.update()
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
						 in_signature='ss', out_signature='i')
	def upgrade(self,args,extraParms):
		action='upgrade'
		ret=self.rebost.execute(action,args,extraParms)
		return (ret)

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
