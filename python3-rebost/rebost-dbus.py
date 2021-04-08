#!/usr/bin/env python3
import sys
import time
import signal
import dbus,dbus.service,dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import rebostCore as rebost


class rebostDbusMethods(dbus.service.Object):
	def __init__(self,bus_name,*args,**kwargs):
		super().__init__(bus_name,"/net/lliurex/rebost")
		self.rebost=rebost.Rebost()
		self.rebost.run()

	def _debug(self,msg):
		if self.dbg:
			print("rebost: %s"%str(msg))
	
	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='i')
	def install(self,args,extraArgs):
		action='install'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='i')
	def load(self,args,extraArgs):
		action='load'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='s')
	def search(self,args,extraArgs=''):
		action='search'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='i')
	def listAll(self,args,extraArgs):
		action='list'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)
	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='i')
	def search_by_category(self,args,extraArgs):
		action='list'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='s')
	def show(self,args,extraArgs):
		action='show'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
                         in_signature='ss', out_signature='i')
	def remove(self,args,extraArgs):
		action='remove'
		ret=self.rebost.execute(action,args,extraArgs)
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
	def upgrade(self,args,extraArgs):
		action='upgrade'
		ret=self.rebost.execute(action,args,extraArgs)
		return (ret)

	@dbus.service.method("net.lliurex.rebost",
                         in_signature='i', out_signature='s')
	def chkProgress(self,procId=0):
		ret=self.rebost.chkProgress(procId)
		return (ret)
	
	@dbus.service.method("net.lliurex.rebost",
                         in_signature='i', out_signature='s')
	def getResults(self,procId=0):
		ret=self.rebost.getResults(procId)
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
											bus=dbus.SessionBus(),
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

test=rebostDBus()
