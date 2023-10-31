#!/usr/bin/env python3
import os,shutil
import gi
from gi.repository import Gio
import json
import rebostHelper
import html
import sqlite3
import subprocess
from shutil import copyfile
import time
import appimageHelper

class sqlHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		self.enabled=True
		self.gui=False
		self.actions=["show","search","load","list",'commitInstall','getCategories','disableFilters']
		self.packagekind="*"
		self.priority=100
		self.postAutostartActions=["load"]
		self.store=None
		self.wrkDir="/usr/share/rebost"
		self.softwareBlackList=os.path.join(self.wrkDir,"lists.d/blacklist")
		self.softwareWhiteList=os.path.join(self.wrkDir,"lists.d/whitelist")
		self.bannedWordsList=os.path.join(self.wrkDir,"lists.d/words")
		self.main_table=os.path.join(self.wrkDir,"rebostStore.db")
		self.installed_table=os.path.join(self.wrkDir,"installed.db")
		self.categories_table=os.path.join(self.wrkDir,"categories.db")
		self.proc_table=os.path.join(self.wrkDir,"rebostPrc.db")
		self.main_tmp_table=os.path.join(self.wrkDir,"tmpStore.db")
		if os.path.isfile(self.main_tmp_table):
			os.remove(self.main_tmp_table)
		self.appimage=appimageHelper.appimageHelper()
		self.lastUpdate="/usr/share/rebost/tmp/sq.lu"
		self.blacklist=True
		self.blacklistFilter=rebostHelper.getFiltersList(blacklist=True)
		self.whitelist=True
		self.whitelistFilter=rebostHelper.getFiltersList(whitelist=True)
		self.wordlistFilter=rebostHelper.getFiltersList(wordlist=True)
		self.noShowCategories=["GTK","QT","Qt","Kde","KDE","Java","Gnome","GNOME"]
	#def __init__

	def setDebugEnabled(self,enable=True):
		self.dbg=enable
		self._debug("Debug {}".format(self.dbg))
	#def setDebugEnabled

	def _log(self,msg):
		dbg="sql: {}".format(msg)
		rebostHelper.logmsg(dbg)
	#def _debug

	def _debug(self,msg):
		if self.dbg:
			dbg="sql: {}".format(msg)
			rebostHelper._debug(dbg)
	#def _debug

	def _getWordsFilter(self):
		#Default banned words list. If there's a banned words list file use it
		bannedWordsFile=os.path.join(self.bannedWordsList,"bannedWords.conf")
		wordblacklist=['cryptocurrency','cryptocurrencies','wallet','bitcoin','monero','Wallet','Bitcoin','Cryptocurrency','Monero','Mine','miner','mine','mining','Mining',"btc","BTC","Btc","Ethereum","ethereum"]
		if os.path.isfile(bannedWordsFile):
			fwordlist=[]
			with open(bannedWordsFile,'r') as f:
				for line in f.readlines():
					fwordlist.append(line.strip())
			if len(fwordlist)>0:
				wordblacklist=fwordlist
		return (wordblacklist)
	#def _getWordsFilter

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		rs='[{}]'
		if action=='search':
			rs=self._searchPackage(parms)
		if action=='list':
			rs=self._listPackages(parms,extraParms,**kwargs)
		if action=='show':
			rs=self._showPackage(parms,extraParms)
		if action=='load':
			rs=self.consolidateSqlTables()
		if action=='commitInstall':
			rs=self._commitInstall(parms,extraParms,extraParms2)
		if action=='getCategories':
			rs=self._getCategories()
		if action=='disableFilters':
			self.whitelist=not(self.whitelist)
			if os.path.isfile(self.lastUpdate)==True:
				os.remove(self.lastUpdate)
			rs=self.consolidateSqlTables()
			#self.whitelist=True
		return(rs)
	#def execute

	def enableConnection(self,table,extraFields=[],tableName='',onlyExtraFields=False):
		if tableName=='':
			tableName=os.path.basename(table).replace(".db","")
		elif tableName.endswith('.db'):
			tableName=os.path.basename(tableName).replace(".db","")
		else:
			tableName=os.path.basename(tableName)
		db=sqlite3.connect(table)
		cursor=db.cursor()
		fields=",".join(extraFields)
		if onlyExtraFields==False:
			if fields:
				fields=","+fields
			query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT{});".format(tableName,fields)
		else:
			query="CREATE TABLE IF NOT EXISTS {} ({});".format(tableName,fields)
		cursor.execute(query)
		return(db,cursor)
	#def enableConnection

	def closeConnection(self,db):
		db.commit()
		db.close()
	#def closeConnection

	def _getCategories(self):
		table=os.path.basename(self.categories_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.categories_table,extraFields=["category TEXT PRIMARY KEY"],onlyExtraFields=True)
		query="SELECT * FROM {} ORDER BY category;".format(table)
		cursor.execute(query)
		rows=cursor.fetchall()
		self.closeConnection(db)
		return(rows)
	#def _searchPackage

	def _showPackage(self,pkgname,user=''):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT"])
		query="SELECT pkg,data FROM {} WHERE pkg = '{}' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rowsTmp=cursor.fetchall()
		rows=[]
		for row in rowsTmp:
			(pkg,data)=row
			rebostPkg=json.loads(data)
			bundles=rebostPkg.get('bundle',{})
			#Update state for bundles as they can be installed outside rebost
			for bundle in bundles.keys():
				if bundle=='appimage':
					app=bundles.get(bundle,'')
					if not app.lower().endswith(".{}".format(bundle)) and app!='':
						dataTmp=self.appimage.fillData(data)
						row=(pkg,dataTmp)
						query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(table,dataTmp,pkgname)
						try:
							cursor.execute(query)
						except:
							print("Query error upgrading appimage: {}".format(query))
							
						db.commit()
						rebostPkg=json.loads(dataTmp)
				#Get state from epi
				(epi,script)=rebostHelper.generate_epi_for_rebostpkg(rebostPkg,bundle,user)
				state=rebostHelper.get_epi_status(script)
				tmpDir=os.path.dirname(epi)
				if os.path.isdir(tmpDir):
					try:
						shutil.rmtree(tmpDir)
					except Exception as e:
						self._debug("Couldn't remove tmpdir {}: {}".format(tmpDir,e))

				if state!=rebostPkg['state'].get(bundle,''):
					rebostPkg['state'].update({bundle:state})
					query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(table,json.dumps(rebostPkg),pkgname)
					try:
						cursor.execute(query)
					except:
						print("Query error updating state: {}".format(query))
					db.commit()
			rebostPkg['description']=rebostHelper._sanitizeString(rebostPkg['description'],unescape=True)
			rebostPkg['summary']=rebostHelper._sanitizeString(rebostPkg['summary'])
			rebostPkg['name']=rebostHelper._sanitizeString(rebostPkg['name'])
			row=(pkg,json.dumps(rebostPkg))
			rows.append(row)
		self.closeConnection(db)
		return(rows)
	#def _showPackage

	def _searchPackage(self,pkgname):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT"])
		query="SELECT pkg,data FROM {} WHERE pkg LIKE '%{}%' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		self.closeConnection(db)
		return(rows)
	#def _searchPackage

	def _listPackages(self,category='',limit=0,**kwargs):
		installed=kwargs.get('installed',False)
		upgradable=kwargs.get('upgradable',False)
		if isinstance(category,list):
			category=category[0]
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT"])
		fetch=''
		order="ORDER BY pkg"
		if isinstance(limit,int)==False:
			limit=0
		if limit>0:
			fetch="LIMIT {}".format(limit)
			order="ORDER by RANDOM()"
		if upgradable or installed:
			query="SELECT pkg,data FROM {0} WHERE data LIKE '%\"state\": _\"_____%\": \"0\"%}}' {2} {3}".format(table,str(category),order,fetch)
		else:
			if "," in category:
				query="SELECT pkg,data FROM {0} WHERE cat0 in {1} OR cat1 in {1} OR cat2 in {1} {2} {3}".format(table,str(category),order,fetch)
			else:
				query="SELECT pkg,data FROM {0} WHERE '{1}' in (cat0,cat1,cat2) {2} {3}".format(table,str(category),order,fetch)
		self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		if (len(rows)<limit) or (len(rows)==0):
			query="PRAGMA case_sensitive_like = 1"
			cursor.execute(query)
			query="SELECT pkg,data FROM {0} WHERE data LIKE '%categories%{1}%' {2} {3}".format(table,str(category),order,fetch)
			cursor.execute(query)
			moreRows=cursor.fetchall()
			if moreRows:
				rows.extend(moreRows)
			query="PRAGMA case_sensitive_like = 0"
			cursor.execute(query)
		self.closeConnection(db)
		return(rows)
	#def _listPackages

	def _commitInstall(self,pkgname,bundle='',state=0):
		#self._debug("Setting status of {} {} as {}".format(pkgname,bundle,state))
		self._log("Setting status of {} {} as {}".format(pkgname,bundle,state))
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT"])
		(dbInstalled,cursorInstalled)=self.enableConnection(self.installed_table,["pkg TEXT","bundle TEXT","release TEXT","state TEXT","PRIMARY KEY (pkg, bundle)"],onlyExtraFields=True)
		query="SELECT pkg,data FROM {} WHERE pkg='{}';".format(table,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		for row in rows:
			(pkg,dataContent)=row
			data=json.loads(dataContent)
			data['state'][bundle]=state
			release=data['versions'].get(bundle,0)
			if isinstance(data['installed'],str):
				data['installed']={}
			if state!=0:
				data['installed'].pop(bundle,None)
			else:
				data['installed'][bundle]=release
			dataContent=str(json.dumps(data))
			#Ensure all single quotes are duplicated or sql will fail
			dataContent=dataContent.replace("''","'")
			dataContent=dataContent.replace("'","''")
			query="UPDATE {0} SET data='{1}' WHERE pkg='{2}';".format(table,dataContent,pkgname)
			queryInst="INSERT or REPLACE INTO {0} VALUES(?,?,?,?);".format(os.path.basename(self.installed_table).replace(".db",""))
			cursorInstalled.execute(queryInst,(pkgname,bundle,release,state))
		#self._debug(query)
			cursor.execute(query)
		self.closeConnection(db)
		self.closeConnection(dbInstalled)
		return(rows)
	#def _commitInstall

	def consolidateSqlTables(self):
		self._debug("Merging data")
		consolidate_table="packagekit.db"
		main_tmp_table=os.path.basename(self.main_table).replace(".db","")
		#Update?
		update=self._chkNeedUpdate()
		if update==False:
			self._debug("Skip merge")
			self._log("Database ready. Rebost operative")
			return([])
		sources=self._getEnabledSources()
		fupdate=open(self.lastUpdate,'w')
		if os.path.isfile(os.path.join(self.wrkDir,consolidate_table)) and sources.get("package",True)==True:
			fsize=os.path.getsize(os.path.join(self.wrkDir,consolidate_table))
			fupdate.write("{0}: {1}".format(consolidate_table,fsize))
			#self.copyBaseTable()
		(main_db,main_cursor)=self.enableConnection(self.main_tmp_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT"],tableName=main_tmp_table)
		#Begin merge
		tables=["appstream","flatpak","snap","appimage","packagekit"]
		include=[]
		for source in sources.keys():
			if source in tables:
				if sources[source]==False:
					idx=tables.index(source)
					tables.pop(idx)
		for table in tables:
			include.append("{}.db".format(table))
		allCategories=[]
		for fname in include:
			(count,categories)=self._processDatabase(fname,main_db,main_cursor,main_tmp_table,fupdate)
			allCategories.extend(categories)
			allCategories=list(set(allCategories))
		fupdate.close()
		self.closeConnection(main_db)
		if len(allCategories)>0:
			self._processCategories(allCategories)
		self._copyTmpDef()
		self._generateCompletion()
		return([])
	#def consolidateSqlTables

	def _getEnabledSources(self):
		config=os.path.join(self.wrkDir,"store.json")
		fcontent={}
		if os.path.isfile(config):
			with open(config,'r') as f:
				fcontent=json.loads(f.read())
		return(fcontent)
	#def _getEnabledSources(self):

	def _processDatabase(self,fname,db,cursor,tmpdb,fupdate):
		allCategories=[]
		retval=(0,[])
		f=os.path.join(self.wrkDir,fname)
		if os.path.isfile(f):
			fsize=os.path.getsize(f)
			fupdate.write("\n{0}:{1}".format(fname,fsize))
			allData=self._getAllData(f)
			(offset,limit,step)=(0,0,2000)
			count=len(allData)
			while limit<count:
				limit+=step
				if limit>count:
					limit=count
				self._debug("Fetch from {0} to {1}. Max {2}".format(offset,limit,count))
				query=[]
				for data in allData[offset:limit]:
					processedPkg=self._addPkgToQuery(tmpdb,cursor,data,fname)
					if processedPkg!=([],[]):
						pkgData=processedPkg[0]
						categories=processedPkg[1]
						if len(categories)>0:
							allCategories.extend(categories)
						query.append(pkgData)
				queryMany="INSERT or REPLACE INTO {} VALUES (?,?,?,?,?)".format(tmpdb)
				try:
					cursor.executemany(queryMany,query)
					db.commit()
				except Exception as e:
					self._debug(e)
					self._debug(query)
				offset=limit+1
				if offset>count:
					offset=count
			allCategories=list(set(allCategories))
			retval=(count,allCategories)
		return(retval)
	#def _processDatabase

	def _processCategories(self,allCategories):
		self._debug("Populating categories")
		categories_table=os.path.basename(self.categories_table).replace(".db","")
		(db_cat,cursor_cat)=self.enableConnection(self.categories_table,extraFields=["category TEXT PRIMARY KEY"],onlyExtraFields=True)
		queryDelete="DELETE FROM {}".format(categories_table)
		cursor_cat.execute(queryDelete)
		queryCategories="INSERT or REPLACE INTO {} VALUES (?);".format(categories_table)
		try:
			for cat in allCategories:
				if cat!='' and isinstance(cat,str):
					#cat=cat.capitalize().strip()
					cat=cat.strip()
					cursor_cat.execute(queryCategories,(cat,))
		except Exception as e:
			self._debug(e)
		self._debug(queryCategories)
		self.closeConnection(db_cat)
	#def _processCategories

	def _addPkgToQuery(self,table,cursor,data,fname):
		(cat0,cat1,cat2)=(None,None,None)
		retval=([],[])
		(pkgname,pkgdata)=data
		pkgdataJson=json.loads(pkgdata)
		blacklisted=False
		if self.blacklist==True:
			blacklisted=self._checkBlacklisted(pkgname,pkgdataJson)
		if self.whitelist==True:
			blacklisted=not(self._checkWhitelisted(pkgname,pkgdataJson,blacklisted))
		if blacklisted==False:
			categories=pkgdataJson.get('categories',[])
			if not ("Lliurex" in categories) and not("LliureX" in categories):
				description=pkgdataJson.get('description','')
				if (isinstance(description,str)==False) or (description==''):
					description=str(pkgdataJson.get('summary',''))
				description=description.replace("-"," ")
				description=description.replace("."," ")
				description=description.replace(","," ")
				for word in self.wordlistFilter.get('words',[]):
					if word in description:
						blacklisted=True
						break
		if blacklisted==True:
			return(retval)
		fetchquery="SELECT * FROM {0} WHERE pkg = '{1}'".format(table,pkgname)
		row=cursor.execute(fetchquery).fetchone()
		if row:
			pkgdataJson=self._mergePackage(pkgdataJson,row,fname).copy()
		#elif "packagekit" in fname.lower():
		#	return(retval)
		if pkgdataJson.get('bundle',{})!={}:
			categories=pkgdataJson.get('categories',[])
			if "Lliurex" in categories:
				idx=categories.index("Lliurex")
				if idx!=0:
					pkgdataJson['categories'][0]=categories[idx]
					pkgdataJson['categories'][idx]=categories[0]
				categories=pkgdataJson.get('categories',[])
			categoriesSet=list(set(categories)-set(self.noShowCategories))
			categories=categoriesSet
				
			while len(categories)<3:
				categories.append("")
			if ("Lliurex" in categories):
				cat0="Lliurex"
				cat1=categories[0]
				cat2=categories[-1]
			else:
				cat0=categories[0]
				cat1=categories[-1]
				cat2=categories[-2]
			if isinstance(pkgdataJson['versions'],dict):
				states=pkgdataJson.get('state')
				pkgdataJson['installed']={}
				for bun,state in states.items():
					if state=="0":
						pkgdataJson['installed'][bun]=pkgdataJson.get('versions',{}).get(bun,0)
			pkgdata=str(json.dumps(pkgdataJson))
			retval=([pkgname,pkgdata,cat0,cat1,cat2],categories)
		return(retval)
	#def _addPkgToQuery

	def _checkBlacklisted(self,pkgname,data,blacklisted=False):
		filters=self.blacklistFilter.get('blacklist',{})
		categories=data.get('categories')
#		if "Lliurex" not in categories and "LliureX" not in categories:
		blackC=list(set(filters.get('categories',[])))
		fcategories=list(set(categories))
		#REM: len==len(set) -> no matching categories
		if len(blackC+fcategories)!=len(set(blackC+fcategories)):
			blacklisted=True
		#endif "Lliurex"...
		apps=filters.get('apps',[]) 
		globs=[ c for c in apps if c.endswith("*")]
		apps=[ c for c in apps if not c.endswith("*")]
		if blacklisted==False:
			if pkgname in apps:
				blacklisted=True
			else:
				for glob in globs:
					if pkgname.startswith("libreof"):
						break
					if pkgname.startswith(glob.replace("*","")):
						blacklisted=True
		return(blacklisted)
	#def _checkBlacklisted

	def _checkWhitelisted(self,pkgname,data,blacklisted=False):
		whitelisted=False
		categorySet=list(set(data.get('categories',[])))
		filters=self.whitelistFilter.get('whitelist',{})
		whiteC=list(set(filters.get('categories',[])))
		if len(filters.get('apps',[]))==0 and len(whiteC)==0:
			whitelisted=not(blacklisted)
		else:
			if len(filters.get('apps',[]))>0:
				if pkgname in filters.get('apps',[]):
					whitelisted=True
				else:
					whitelisted=False
			if len(whiteC)>0 and whitelisted==False:
				if len(whiteC+categorySet)!=len(set(whiteC+categorySet)):
					whitelisted=True
				else:
					whitelisted=False
		#if "Lliurex" in categorySet or "LliureX" in categorySet:
		#	whitelisted=True
		return(whitelisted)
	#def _checkWhitelisted

	def _generateCompletion(self):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT"])
		query="SELECT pkg FROM {};".format(table)
		cursor.execute(query)
		rows=cursor.fetchall()
		completionFile="/usr/share/rebost/tmp/bash_completion"
		if os.path.isdir(os.path.dirname(completionFile)):
			with open(completionFile,'w') as f:
				for row in rows:
					f.write("{}\n".format(row[0]))
		self.closeConnection(db)
	#def _generateCompletion

	def _chkNeedUpdate(self):
		update=False
		include=["appimage.db","flatpak.db","snap.db","zomandos.db","appstream.db"]
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
			update=True
		else:
			with open(self.lastUpdate,'r') as f:
				fcontent=f.readlines()
			for fname in include:
				f=os.path.join(self.wrkDir,fname)
				fsize=0
				if os.path.isfile(f):
					fsize=os.path.getsize(f)
				for f in fcontent:
					if fname in f:
						fValues=f.split(":")
						if fValues[-1].strip()!=str(fsize):
							update=True
							break
				if update:
					break
		return(update)
	#def _chkNeedUpdate

	def _getAllData(self,f):
		allData=[]
		table=os.path.basename(f).replace(".db","")
		self._debug("Accesing {}".format(f))
		(db,cursor)=self.enableConnection(f,["cat0 TEXT","cat1 TEXT","cat2 TEXT"])
		query="SELECT pkg,data FROM {}".format(table)
		cursor.execute(query)
		allData=cursor.fetchall()
		self.closeConnection(db)
		return (allData)
	#def _getAllData

	def _mergePackage(self,pkgdataJson,row,fname):
		(pkg,data,cat0,cat1,cat2)=row
		mergepkgdataJson=json.loads(data)
		for key,item in pkgdataJson.items():
			if not key in mergepkgdataJson.keys():
				mergepkgdataJson[key]=item
			elif isinstance(item,dict) and isinstance(mergepkgdataJson.get(key,''),dict):
				if len(item)>0:
					mergepkgdataJson[key].update(item)
			elif isinstance(item,list) and isinstance(mergepkgdataJson.get(key,''),list):
				if len(item)>0:
					mergepkgdataJson[key].extend(item)
					mergepkgdataJson[key] = list(set(mergepkgdataJson[key]))
			elif isinstance(item,str) and isinstance(mergepkgdataJson.get(key,None),str):
				#if (fname=="appstream.db") and (len(mergepkgdataJson.get(key,''))<len(item)):
				#	mergepkgdataJson[key]=item
				#elif len(item)>len(mergepkgdataJson.get(key,'')):
				if len(item)>len(mergepkgdataJson.get(key,'')):
					mergepkgdataJson[key]=item
		return(mergepkgdataJson)
	#def _mergePackage

	def copyBaseTable(self):
		rebost_db=sqlite3.connect(self.main_tmp_table)
		cursor=rebost_db.cursor()
		table=os.path.basename(self.main_table).replace(".db","")
		consolidate_table="packagekit"
		query="DROP TABLE IF EXISTS {}".format(table)
		cursor.execute(query)
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT, cat0 TEXT, cat1 TEXT, cat2 TEXT);".format(table)
		cursor.execute(query)
		cursor.execute("ATTACH DATABASE '/usr/share/rebost/{}.db' AS pk;".format(consolidate_table))
		cursor.execute("INSERT INTO {0} (pkg,data,cat0,cat1,cat2) SELECT * from pk.{1};".format(table,consolidate_table))
		rebost_db.commit()
		rebost_db.close()
	#def copyBaseTable

	def _copyTmpDef(self):
		#Copy tmp to definitive
		self._debug("Copying {0} to main table {1}".format(self.main_tmp_table,self.main_table))
		copyfile(self.main_tmp_table,self.main_table)
		self._debug("Removing tmp file")
		os.remove(self.main_tmp_table)
		self._log("Database ready. Rebost operative")
	#def _copyTmpDef
	
	def getTableStatus(self,pkg,bundle):
		(dbInstalled,cursorInstalled)=self.enableConnection(self.installed_table,["pkg TEXT","bundle TEXT","release TEXT","state TEXT","PRIMARY KEY (pkg, bundle)"],onlyExtraFields=True)
		query="Select * from installed where pkg={0} and bundle={1}".format(pkg,bundle)
		ret=cursorInstalled.execute(query)
		return ret

def main():
	obj=sqlHelper()
	return (obj)

