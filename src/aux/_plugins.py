#!/usr/bin/python3
import os,sys
import importlib.util

class _rebostPlugins:
	def __init__(self,*args):
		self.core=args[0]
		self.config=self.core.config
		self.DBG=self.core.DBG
	#def __init__

	def _debug(self,msg):
		if self.DBG==True:
			print("import: {}".format(msg))

	def _importPlugin(self,modpath):
		plugin=None
		modname=os.path.basename(modpath).replace(".py","")
		self._debug("Inspecting plugin {} at {}".format(modname,modpath))
		if os.path.exists(modpath):
			try:
				spec = importlib.util.spec_from_file_location("engine",modpath)
				pluginlib = importlib.util.module_from_spec(spec)
				sys.modules["module.name"] = pluginlib
				spec.loader.exec_module(pluginlib)
				pluginmod=pluginlib.engine(self.core)
				
				#if hasattr(pluginlib,"engine")==True:
				if hasattr(pluginmod,"bundle")==True:
					modname=pluginmod.bundle
					self.supportedformats.append(pluginmod.bundle)
				else:
					modname=modname.replace(".py","")
				plugin={modname:pluginmod}
				#else:
				#	self._debug("Discarded {}".format(modname))
			except Exception as e:
				self._error("Failed importing {0}: {1}".format(modpath,e))
		else:
			self._debug("{} not found".format(modpath))
		return(plugin)
	#def _importPlugin

	def loadPlugins(self):
		config=self.config.readConfig()
		CACHE=config["cache"]
		self.supportedformats=[]
		pluginDir=os.path.join(os.path.dirname(os.path.realpath(__file__)),"../","plugins")
		plugins={}
		self._debug("Accessing {}".format(pluginDir))
		if os.path.exists(pluginDir):
			for f in os.scandir(pluginDir):
				pluginfo=None
				if (not f.name.endswith(".py")) or (f.name.startswith("_")):
					continue
				pluginfo=self._importPlugin(f.path)
				if pluginfo!=None:
					plugin=list(pluginfo.values())[0]
					#plugin=pluginfo.get(f.name.replace(".py",""),"")
					if hasattr(plugin,"enabled")==True:
						if plugin.enabled==False:
							self._debug("Disabled plugin {}".format(f.name))
							continue
					priority=100
					if hasattr(plugin,"priority")==True:
						priority=plugin.priority
					if priority not in plugins.keys():
						plugins[priority]={}
					modkey=list(pluginfo.keys())[0]
					plugindict=plugins[priority]
					if plugindict.get(modkey)!=None:
						plugindict[modkey].append(pluginfo[modkey])
					else:
						plugindict.update({modkey:[pluginfo[modkey]]})
		return(self.supportedformats,plugins)
	#def loadPlugins
