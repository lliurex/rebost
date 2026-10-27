#!/usr/bin/python3
import locale
import os,sys,json
from urllib.request import Request,urlopen
import importlib.util

class _rebostAux:
	def __init__(self,*args):
		self.rconfig=args[0]
		self.core=args[1]
		self.DBG=self.core.DBG
	#def __init__

	def _debug(self,msg):
		if self.DBG==True:
			print("aux: {}".format(msg))
	#def _debug

	def _error(self,msg):
		print("aux error: {}".format(msg))
	#def _error(self,msg):

	def getLangs(self):
		localLangs=[]
		for localLang in locale.getlocale():
			if "_" in localLang:
				localLangs.append(localLang.split("_")[0])
				localLangs.append(localLang.split("_")[-1].lower())
		if "ca" in localLangs:
			idx=localLangs.index("ca")
			localLangs.insert(idx+1,"ca-valencia")
			localLangs.insert(idx+1,"ca@valencia")
		localLangs.insert(0,"C")
		langs=list(set(localLangs))
		return(langs)
	#def getLangs

	def releaseChanged(self):
		self.config=self.rconfig.readConfig()
		changed=False
		if os.path.exists(self.config["cache"])==False:
			os.makedirs(self.config["cache"])
		if os.path.exists(os.path.join(self.config["cache"],"raw"))==False:
			os.makedirs(os.path.join(self.config["cache"],"raw"))
		cFile=os.path.join(self.config["cache"],"release")
		cContent="0"
		if os.path.exists(cFile):
			with open(cFile,"r") as f:
				cContent=f.read()
		cRelease=str(cContent)
		if self.config.get("release","1.0")!=cRelease:
			changed=True
		with open(cFile,"w") as f:
			f.write(self.config.get("release","1.0"))
		return(changed)
	#def releaseChanged

	def _getUrlApiFromRaw(self,url):
		if "/github.com" in url:
			apiUrl=[]
			for item in url.split("/"):
				if item=="github.com":
					item="api.github.com/repos"
				elif item=="raw":
					item="contents"
				elif item in ["refs","heads","master"]:
					continue
				apiUrl.append(item)
			if len(apiUrl)>0:
				url="/".join(apiUrl)
				url+="?ref=master"
		return(url)
	#def _getUrlApiFromRaw

	def _chkRemoteFileChanged(self,url):
		changed=False
		print("GET URL: {}".format(url))
		oldETag=""
		fname=url.split("://")[-1]
		fname=fname.replace("/","_")
		fTag=os.path.join(self.CACHE,"{}.etag".format(fname))
		try:
			with open(fTag,"r") as f:
				oldETag=json.load(f)
		except:
			oldETag={}
		print("GET URL: {}".format(url))
		self._debug("Check ETag: {}".format(oldETag))
		if isinstance(oldETag,dict)==False:
			oldETag={}
		headers={"user-agent":'Python-urllib-SHA-Checker/1.0'}
		url=self._getUrlApiFromRaw(url)
		self._debug("API URL: {}".format(url))
		req=Request(url,headers=headers)
		try:	
			with urlopen(req,timeout=2) as f:
				resp=json.loads(f.read().decode("utf8"))
				ETag=resp.get("sha")
				if ETag!=oldETag:
					changed=True
					with open(fTag,"w") as f:
						json.dump(ETag,f)
					oldETag=ETag
		except Exception as e:
			print(e)
			pass
		self._debug("Check ETag end: {}".format(oldETag))
		return(changed)
	#def _chkRemoteFileChanged

	def cleanFiles(self):
		main=os.path.join(self.config["cache"],"main.xml")
		if os.path.exists(main):
			os.unlink(main)
		rawDir=os.path.join(self.config["cache"],"raw")
		if os.path.exists(rawDir):
			for f in os.scandir(rawDir):
				if f.is_dir()==False:
					os.unlink(f.path)
				else:
					for f2 in os.scandir(f.path):
						if f2.is_dir()==False:
							os.unlink(f2.path)
	#def cleanFiles

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
		self.config=self.rconfig.readConfig()
		self.CACHE=self.config["cache"]
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
