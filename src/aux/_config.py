#!/usr/bin/python3
import json,os

CONFIG="/usr/share/rebost/rebost.conf"
class _rebostConfig:
	def __init__(self,*args):
		self.dbg=False
		self.config={}
	#def __init__

	def readConfig(self,update=False):
		if update==True:
			self.config={}
		if len(self.config)==0:
			if os.path.isfile(CONFIG):
				fcontent=""
				with open(CONFIG,"r") as f:
					fcontent=f.read()
				self.config=json.loads(fcontent)
		self.config["cache"]="/var/cache/rebost"
		self.config["data"]="/usr/share/rebost-data"
		return(self.config)
	#def readConfig(self):

	def _getVerifiedOrigins(self,stores):
		config=self.readConfig()
		matchTables=config.get("verifiedProvider",[])
		verifiedOrigins=[]
		for matchTable in matchTables:
			for idx,store in stores.items():
				if isinstance(idx,int)==False:
					continue
				if store.get_origin()==matchTable:
					verifiedOrigins.append(idx)
		return(verifiedOrigins)
	#def _getVerifiedOrigins

