#!/usr/bin/python3
import locale
import os,sys,json
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET

class _rebostAux:
	def __init__(self,*args):
		self.core=args[0]
		self.config=self.core.config
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
		config=self.config.readConfig()
		changed=False
		if os.path.exists(config["cache"])==False:
			os.makedirs(config["cache"])
		if os.path.exists(os.path.join(config["cache"],"raw"))==False:
			os.makedirs(os.path.join(config["cache"],"raw"))
		cFile=os.path.join(config["cache"],"release")
		cContent="0"
		if os.path.exists(cFile):
			with open(cFile,"r") as f:
				cContent=f.read()
		cRelease=str(cContent)
		if config.get("release","1.0")!=cRelease:
			changed=True
		with open(cFile,"w") as f:
			f.write(config.get("release","1.0"))
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
		oldETag=""
		fname=url.split("://")[-1]
		fname=fname.replace("/","_")
		CACHE=self.config.readConfig().get("cache","/tmp")
		fTag=os.path.join(CACHE,"{}.etag".format(fname))
		try:
			with open(fTag,"r") as f:
				oldETag=json.load(f)
		except:
			oldETag={}
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
		cache=self.config.readConfig().get("cache","/tmp")
		fxml=os.path.join(cache,"main.xml")
		if os.path.exists(fxml):
			os.unlink(fxml)
		raw=os.path.join(cache,"raw")
		if os.path.exists(raw):
			if os.path.isdir(raw):
				for f in os.scandir(raw):
					if f.is_file()==True:
						os.unlink(f.path)
					elif f.is_dir()==True:
						for ff in os.scandir(f.path):
							os.unlink(ff.path)
		if os.path.exists(cache):
			for f in os.scandir(cache):
				if f.name.endswith(".map"):
					os.unlink(f.path)
	#def cleanFiles

	def fixMalformedXml(self,fxml):
		with open(fxml,"r") as f:
			fcontent=f.read()
		fcontent=fcontent.replace("&lt;","").replace("&gt","").replace("&"," &amp;")
		tree = ET.fromstring(fcontent)
		r=tree.getroot()
		for description in r.iter('description'):
			txt=[]
			for i in list(description):
				desc=i.text
				if isinstance(desc,str)==False:
					desc=""
				description.remove(i)
				txt.append(desc.strip())
			text=html.escape("{}".format(txt))
			desc="<p>{}</p>".format(text)
			try:
				elem=ET.fromstring(desc)
			except Exception as e:
				self._error(e,msg="_fromFile")
			description.append(elem)
		os.unlink(fxml)
		tree.write(fxml,xml_declaration="1.0",encoding="UTF-8")
	#def fixMalformedXml
