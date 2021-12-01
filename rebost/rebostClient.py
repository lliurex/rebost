#!/usr/bin/env python3
import sys,os
import subprocess
import json
import signal
import ast
import dbus,dbus.exceptions
import logging
import getpass

class RebostClient():
	def __init__(self,*args,**kwargs):
		self.dbg=False
		logging.basicConfig(format='%(message)s')
		self.user=''
		self.n4dkey=''
		if kwargs:
			self.user=kwargs.get('user','')
		if self.user=='':
			self.user=getpass.getuser()
		if self.user=='root':
		#check that there's no sudo
			sudo_user=os.environ.get("SUDO_USER",'')
			if sudo_user:
				self.user=sudo_user
#		self._debug("Selected user: {}".format(self.user))
		self.rebost=None

	def _debug(self,msg):
		if self.dbg:
			logging.warning("rebost: %s"%str(msg))
	#def _debug

	def _connect(self):
		try:
			bus=dbus.SystemBus()
		except Exception as e:
			print("Could not get session bus: %s\nAborting"%e)
			sys.exit(1)
		try:
			self.rebost=bus.get_object("net.lliurex.rebost","/net/lliurex/rebost")
		except Exception as e:
			print("Could not connect to bus: %s\nAborting"%e)
			sys.exit(1)
	
	def execute(self,action,args='',extraParms=''):
		if self.n4dkey=='':
			self.n4dkey=self._getN4dKey()
		self._connect()
		procId=0
		if isinstance(args,str):
			args=[args]
		if args:
			for arg in args:
				if ":" in arg:
					package=arg.split(":")
					extraParms=package[-1]
					package=package.pop(0)
				else:
					package=arg
				try:
				#	if "-" in package:
				#		package=package.replace("-","_")

					if action=='install':
						if extraParms=="zomando":
							zmdPath=os.path.join("/usr/share/zero-center/zmds","{}.zmd".format(package))
							if os.path.isfile(zmdPath)==True:
								procId=subprocess.run([zmdPath]).returncode
						else:
							procId=self.rebost.install(package,extraParms,self.user,self.n4dkey)
					elif action=='search':
						procId=self.rebost.search(package)
					elif action=='list':
						procId=self.rebost.search_by_category(package)
					elif action=='show':
						procId=self.rebost.show(package,self.user)
					if action=='remove':
						if extraParms=="zomando":
							extraParms="package"
						procId=self.rebost.remove(package,extraParms,self.user,self.n4dkey)
					if action=='enableGui':
						if arg.lower()=="true":
							arg=True
						else:
							arg=False
						self.rebost.enableGui(arg)
					if action=='test':
						procId=self.rebost.test(package,extraParms,self.user)
				except dbus.exceptions.DBusException as e:
					procId=0
					print("Dbus Error: %s"%e)
				except Exception as e:
					procId=0
					print("Err: %s"%e)
				finally:
					self.rebost=None
		else:
			try:
				if action=='update':
					procId=self.rebost.update()
				if action=='fullupdate':
					procId=self.rebost.fullUpdate()
				if action=='load':
					procId=self.rebost.load(package,extraParms)
			except dbus.exceptions.DBusException as e:
				procId=0
				print("Dbus Error: %s"%e)
			except Exception as e:
				procId=0
				print("Err: %s"%e)
			finally:
				self.rebost=None

		return(str(procId))

	def fullUpdate(self,procId=0):
		self._connect()
		bus=self.rebost.fullUpdate()
		progressDict=json.loads(bus)
		self.rebost=None
		return(progressDict)

	def update(self,procId=0):
		self._connect()
		bus=self.rebost.update()
		progressDict=json.loads(bus)
		self.rebost=None
		return(progressDict)

	def getProgress(self,procId=0):
		self._connect()
		bus=self.rebost.getResults()
		progressDict=json.loads(bus)
		self.rebost=None
		return(progressDict)
	
	def getResults(self,procId=0):
		self._connect()
		bus=self.rebost.getResults()
		results=json.loads(bus)
		self.rebost=None
		return(results)
	
	def getPlugins(self):
		pass
	
	def _getN4dKey(self):
		n4dkey=''
		try:
			with open('/etc/n4d/key') as file_data:
				n4dkey = file_data.readlines()[0].strip()
		except:
			pass
		return(n4dkey)
