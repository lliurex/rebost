#!/usr/bin/python3
import sys,os,time
from urllib.request import Request,urlopen
import json

class _rebostMap:
	def __init__(self,*args):
		self.core=args[0]
		self.config=self.core.config
		self.aux=self.core.aux
		self.DBG=self.core.DBG
		self.lastCheckedMapping=0
		self.mapFixes={}
	#def __init__

	def _debug(self,msg):
		if self.DBG==True:
			print("map: {}".format(msg))
	#def _debug

	def _getRemoteMapFixes(self,url):
		content={}
		urlContent=""
		if url!="" and isinstance(url,str):
			req=Request(url, headers={'User-Agent':'Mozilla/5.0'})
			try:
				with urlopen(req,timeout=2) as f:
					urlContent=(f.read().decode('utf-8'))
			except Exception as e:
				self._debug("Couldn't fetch {}".format(url))
				self._debug(e)
		if len(urlContent)>0:
			try:
				content=json.loads(urlContent)
			except Exception as e:
				print(e)
				content={}
		return(content)
	#def _getRemoteMapFixes

	def _getLocalMapFixes(self,fpath):
		content={}
		if os.path.exists(fpath):
			with open(fpath,"r") as f:
				try:
					data=f.read()
					content=json.loads(data)
				except Exception as e:
					print("ERROR PROCESSING {}".format(fpath))
					print(e)
					try:
						for line in data.split("\n"):
							if line.strip().startswith("\"upstream\":"):
								content["upstream"]=line.split(":",1)[-1].strip().replace('"','').replace(",","")
								break
					except Exception as e:
						print(e)
		return(content)
	#def _getLocalMapFixes

	def _getLocalMapFiles(self):
		#Load map files from self.DATA
		mapFiles=[]
		config=self.config.readConfig()
		mapDir=os.path.join(config["data"],"lists.d")
		verifyMaps=[ "{}.map".format(verified) for verified in config.get("verifiedProvider",[])]
		verifyMapsPath=[]
		for d in os.scandir(mapDir):
			if d.is_dir():
				for f in os.scandir(d.path):
					if f.is_file() and f.name not in verifyMaps:
						mapFiles.append(f.path)
					elif f.is_file():
						verifyMapsPath.append(f.path)
					
			elif d.is_file():
				if d.name not in verifyMaps:
					mapFiles.append(d.path)
				else:
					verifyMapsPath.append(d.path)
		#Ensure that information will honour the verifiedProviders
		mapFiles.extend(verifyMapsPath)
		return(mapFiles)
	#def _getLocalMapFiles

	def _getCacheMapFiles(self):
		mapFiles=[]
		config=self.config.readConfig()
		for f in os.scandir(config["cache"]):
			if f.name.endswith(".map"):
				mapFiles.append(f.path)
		return(mapFiles)
	#def _getCacheMapFiles

	def _getMapFixes(self):
		if int(time.time())-self.lastCheckedMapping>120 or len(self.mapFixes.get("nodisplay",[]))==0:
			config=self.config.readConfig()
			self.mapFixes={"nodisplay":[],"aliases":{}}
			mapFiles=self._getLocalMapFiles()
			for mapFile in mapFiles:
				if os.path.exists(mapFile) and mapFile.endswith(".map"):
					self._debug("Reading mapF {}".format(mapFile))
					mapFixesF=self._getLocalMapFixes(mapFile)
					rContent={}
					if "upstream" in mapFixesF:
						self._debug("Checking remote URL {}".format(mapFixesF["upstream"]))
						fname=mapFixesF["upstream"].split("://")[-1]
						fname=fname.replace("/","_")
						fcache=os.path.join(config["cache"],"{}".format(fname))
						if self.aux._chkRemoteFileChanged(mapFixesF["upstream"])==True or os.path.exists(fcache)==False:
							rContent=self._getRemoteMapFixes(mapFixesF["upstream"])
							rContent["upstream"]=mapFixesF["upstream"]
							with open(fcache,"w") as f:
								f.write(json.dumps(rContent,indent=4))
						else:
							self._debug("Getting mapping from cache")
							rContent=self._getLocalMapFixes(fcache)
					if len(rContent.get("nodisplay",[]))>0:
						mapFixesF=rContent.copy()
						with open(mapFile,"w") as f:
							f.write(json.dumps(mapFixesF,indent=4))
					if "nodisplay" in mapFixesF:
						self.mapFixes["nodisplay"]=list(set(self.mapFixes["nodisplay"]+mapFixesF["nodisplay"]))
					if "aliases" in mapFixesF:
						self.mapFixes["aliases"].update(mapFixesF.get("aliases",{}))
			self.lastCheckedMapping=int(time.time())
		return(self.mapFixes)
	#def _getMapFixes

	def chkCacheNeedsUpdate(self):
		update=False
		cFiles=self._getCacheMapFiles()
		for cFile in cFiles:
			with open(cFile,"r") as f:
				content=json.loads(f.read())
			if "://" in content.get("upstream",""):
				if self.core.aux._chkRemoteFileChanged(content["upstream"])==True:
					update=True
					break
		return update
	#def chkCacheNeedsUpdate
