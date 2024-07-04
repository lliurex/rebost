#!/usr/bin/env python3
import os,shutil,stat
import gi
from gi.repository import Gio
import json
import rebostHelper
import html
import sqlite3
from shutil import copyfile
import time
import appimageHelper

class sqlHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		self.enabled=True
		self.gui=False
		self.actions=["show","match","search","load","list",'commitInstall','getCategories','disableFilters','export']
		self.packagekind="*"
		self.priority=0
		self.postAutostartActions=["load"]
		self.store=None
		dbCache="/tmp/.cache/rebost"
		self.rebostCache=os.path.join(dbCache,os.environ.get("USER"))
		self.rebostData="/usr/share/rebost/"
		if os.path.exists(self.rebostCache)==False:
			os.makedirs(self.rebostCache)
		os.chmod(self.rebostCache,stat.S_IRWXU )
		self.softwareBanList=os.path.join(self.rebostData,"lists.d/banned")
		self.softwareIncludeList=os.path.join(self.rebostData,"lists.d/include")
		self.bannedWordsList=os.path.join(self.rebostData,"lists.d/words")
		self.main_table=os.path.join(self.rebostCache,"rebostStore.db")
		self.installed_table=os.path.join(self.rebostCache,"installed.db")
		self.categories_table=os.path.join(self.rebostCache,"categories.db")
		self.proc_table=os.path.join(self.rebostCache,"rebostPrc.db")
		self.main_tmp_table=os.path.join(self.rebostCache,"tmpStore.db")
		if os.path.isfile(self.main_tmp_table):
			os.remove(self.main_tmp_table)
		self.appimage=appimageHelper.appimageHelper()
		self.lastUpdate=os.path.join(self.rebostCache,"tmp","sq.lu")
		self.banlist=True
		if self.banlist:
			self.banlistFilter=rebostHelper.getFiltersList(banlist=True)
		self.includelist=True
		if self.includelist:
			self.includelistFilter=rebostHelper.getFiltersList(includelist=True)
		self.wordlistFilter=rebostHelper.getFiltersList(wordlist=True)
		self.restricted=True
		self.mainTableForRestrict="eduapps"
		self._chkDbIntegrity()
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
		wordbanlist=['cryptocurrency','cryptocurrencies','wallet','bitcoin','monero','Wallet','Bitcoin','Cryptocurrency','Monero','Mine','miner','mine','mining','Mining',"btc","BTC","Btc","Ethereum","ethereum"]
		if os.path.isfile(bannedWordsFile):
			fwordlist=[]
			with open(bannedWordsFile,'r') as f:
				for line in f.readlines():
					fwordlist.append(line.strip())
			if len(fwordlist)>0:
				wordbanlist=fwordlist
		return (wordbanlist)
	#def _getWordsFilter

	def _chkDbIntegrity(self):
		integrity=True
		testQueries=["SELECT alias from %% LIMIT 1"]
		include=["packagekit.db","eduapps.db","appimage.db","flatpak.db","snap.db","zomandos.db","appstream.db"]
		for fname in include:
			self._debug("Testing integrity for fname")
			f=os.path.join(self.rebostCache,fname)
			dbname=fname.replace(".db","")
			for testQuery in testQueries:
				(db,cursor)=self.enableConnection(f,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
				query=testQuery.replace("%%",dbname)
				try:
					cursor.execute(query)
					cursor.fetchone()
				except Exception as e:
					print(e)
					self._debug("Integrity check failed")
					self._debug("Purge {}".format(f))
					os.unlink(f)
					integrity=False
		self.closeConnection(db)
		if integrity==False:
			for i in os.scandir(os.path.join(self.rebostCache,"tmp")):
				os.unlink(i.path)
		return(integrity)
	#def _chkDbIntegrity

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		rs='[{}]'
		if action=='search':
			rs=self._searchPackage(parms)
		if action=='list':
			rs=self._listPackages(parms,extraParms,**kwargs)
		if action=='show' or action=="match":
			onlymatch=False
			if action=="match":
				onlymatch=True
			rs=self._showPackage(parms,extraParms,onlymatch=onlymatch)
		if action=='load':
			rs=self.consolidateSqlTables()
		if action=='commitInstall':
			rs=self._commitInstall(parms,extraParms,extraParms2)
		if action=='getCategories':
			rs=self._getCategories()
		if action=='export':
			rs=self._exportRebost()
		if action=='disableFilters':
			self.includelist=not(self.includelist)
			if os.path.isfile(self.lastUpdate)==True:
				os.remove(self.lastUpdate)
			rs=self.consolidateSqlTables()
			#self.includelist=True
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

	def _showPackage(self,pkgname,user='',onlymatch=False):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
		query="SELECT pkg,data FROM {} WHERE pkg = '{}' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rowsTmp=cursor.fetchall()
		if len(rowsTmp)<=0:
			query="SELECT pkg,data FROM {} WHERE alias = '{}' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
			cursor.execute(query)
			rowsTmp=cursor.fetchall()
		rows=rowsTmp.copy()
		if onlymatch==False:
			rows=[]
			for row in rowsTmp:
				(pkg,data)=row
				rebostPkg=json.loads(data)
				bundles=rebostPkg.get('bundle',{}).copy()
				#Update state for bundles as they can be installed outside rebost
				for bundle in bundles.keys():
					if bundle=='appimage':
						bundleurl=bundles.get(bundle,'')
						rebostPkg=self._upgradeAppimageData(db,table,cursor,bundleurl,pkg,rebostPkg)
					#Get state from epi
					rebostPkg=self._getStateFromEpi(db,table,cursor,pkgname,rebostPkg,bundle,user)
				rebostPkg['description']=rebostHelper._sanitizeString(rebostPkg['description'],unescape=True)
				rebostPkg['summary']=rebostHelper._sanitizeString(rebostPkg['summary'])
				rebostPkg['name']=rebostHelper._sanitizeString(rebostPkg['name'])
				if "flatpak" in rebostPkg['icon'] and os.path.exists(rebostPkg['icon'])==False:
					fpath=os.path.dirname(rebostPkg['icon'])
					spath=fpath.split("/")
					idx=0
					if "icons" in spath:
						idx=spath.index("icons")-1
						fpath="/".join(spath[0:idx])
					if os.path.isdir(fpath) and idx>0:
						for d in os.listdir(fpath):
							if os.path.isdir(os.path.join(fpath,d,"icons")):
								rebostPkg['icon']=os.path.join(fpath,d,"/".join(spath[idx+1:]),os.path.basename(rebostPkg['icon']))
				row=(pkg,json.dumps(rebostPkg))
				rows.append(row)
		self.closeConnection(db)
		return(rows)
	#def _showPackage

	def _upgradeAppimageData(self,db,table,cursor,bundleurl,pkg,rebostPkg):
		if not rebostPkg.get("bundle",{}).get("appimage","").lower().endswith(".appimage") and bundleurl!='':
			dataTmp=self.appimage.fillData(rebostPkg)
			row=(pkg,dataTmp)
			#Ensure all single quotes are duplicated or sql will fail
			dataTmp=dataTmp.replace("''","'")
			dataTmp=dataTmp.replace("'","''")
			query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(table,dataTmp,pkg)
			try:
				cursor.execute(query)
			except:
				print("Query error upgrading appimage: {}".format(query))
			db.commit()
			rebostPkg=json.loads(dataTmp)
		return(rebostPkg)
	#def _upgradeAppimageData

	def _getStateFromEpi(self,db,table,cursor,pkgname,rebostPkg,bundle,user):
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
			#Ensure all single quotes are duplicated or sql will fail
			dataContent=json.dumps(rebostPkg)
			dataContent=dataContent.replace("''","'")
			dataContent=dataContent.replace("'","''")
			query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(table,dataContent,pkgname)
			try:
				cursor.execute(query)
			except:
				print("Query error updating state: {}".format(query))
			db.commit()
		return(rebostPkg)
	#def _getStateFromEpi

	def _exportRebost(self):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
		query="SELECT pkg,data FROM {} ORDER BY pkg".format(table)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		rebostPkgList=[]
		for row in rows:
			rebostPkgList.append(json.loads(row[1]))
		self.closeConnection(db)
		return(rebostHelper.rebostToAppstream(rebostPkgList))
	#def _exportRebost

	def _searchPackage(self,pkgname):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT,alias TEXT"])
		query="SELECT pkg,data FROM {} WHERE pkg LIKE '%{}%' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		self.closeConnection(db)
		return(rows)
	#def _searchPackage

	def _filterUpgradables(self,rows,user):
		filterData=[]
		for pkgname,strpkg in rows:
			pkg=json.loads(strpkg)
			states=pkg.get('state',{})
			installed=pkg.get('installed',{})
			if isinstance(installed,dict)==False:
				installed={}
			versions=pkg.get('versions',{})
			for bundle,state in states.items():
				if state=="0":
					if bundle!="zomando":
						if bundle=='appimage':
							self._debug("Upgrading {} info...".format(pkg.get('pkgname','')))
							ret=self._showPackage(pkg.get('pkgname'),user)
							if len(ret)<=0:
								continue
							retname,retdata=ret[0]
							app=json.loads(retdata)
							versions=app.get('versions',{})
							self._debug(app)
						installedStr=installed.get(bundle,0)
						if ((installedStr!=versions.get(bundle,0)) and (installedStr!=0)):
							filterData.append(strpkg)
		return(filterData)
	#def _filterUpgradables

	def _listPackages(self,category='',limit=0,**kwargs):
		installed=kwargs.get('installed',False)
		upgradable=kwargs.get('upgradable',False)
		user=kwargs.get('user',"")
		if isinstance(category,list):
			category=category[0]
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
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
		if len(rows)<limit or len(rows)==0 and (upgradable==False and installed==False):
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
		if upgradable==True:
			rows=self._filterUpgradables(rows,user)
		return(rows)
	#def _listPackages

	def _commitInstall(self,pkgname,bundle='',state=0):
		#self._debug("Setting status of {} {} as {}".format(pkgname,bundle,state))
		self._log("Setting status of {} {} as {}".format(pkgname,bundle,state))
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
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
		main_tmp_table=os.path.basename(self.main_table).replace(".db","")
		#Update?
		update=self._chkNeedUpdate()
		if update==False:
			self._debug("Skip merge")
			self._log("Database ready. Rebost operative")
			return([])
		sources=self._getEnabledSources()
		fupdate=open(self.lastUpdate,'w')
		if len(self.mainTableForRestrict)>0:
			restrictTablePath=os.path.join(self.rebostCache,"{}.db".format(self.mainTableForRestrict))
			if self.mainTableForRestrict in sources:
				sources.pop(self.mainTableForRestrict)
			if os.path.isfile(restrictTablePath):
				self._debug("Setting {} as main table".format(self.mainTableForRestrict))
				fsize=os.path.getsize(restrictTablePath)
				fupdate.write("{0}: {1}".format(self.mainTableForRestrict,fsize))
				self.copyBaseTable(self.mainTableForRestrict)
		(main_db,main_cursor)=self.enableConnection(self.main_tmp_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"],tableName=main_tmp_table)
		#Begin merge
		tables=["flatpak","snap","appimage","packagekit"]
		include=[]
		for source in sources.keys():
			if source in tables:
				if sources[source]==False:
					idx=tables.index(source)
					tables.pop(idx)
		for table in tables:
			include.append("{}.db".format(table))
		include.insert(0,"appstream.db")
		include.insert(0,"zomandos.db")
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
		config=os.path.join(self.rebostCache,"store.json")
		fcontent={}
		if os.path.isfile(config):
			with open(config,'r') as f:
				fcontent=json.loads(f.read())
		return(fcontent)
	#def _getEnabledSources(self):

	def _processDatabase(self,fname,db,cursor,tmpdb,fupdate):
		allCategories=[]
		retval=(0,[])
		f=os.path.join(self.rebostCache,fname)
		if os.path.isfile(f):
			restricted=self.restricted
			if "zomandos"==fname.replace(".db",""):
				restricted=False
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
				removequery=[]
				for data in allData[offset:limit]:
					(processedPkg,aliasPkg)=self._addPkgToQuery(tmpdb,cursor,data,restricted)
					if processedPkg!=([],[]):
						pkgData=processedPkg[0]
						categories=processedPkg[1]
						if len(categories)>0:
							allCategories.extend(categories)
						query.append(pkgData)
					if aliasPkg!=([],[]):
						app=aliasPkg[0]
						dataContent=aliasPkg[0][1]
						alias=aliasPkg[0][0]
						#Ensure all single quotes are duplicated or sql will fail
						dataContent=dataContent.replace("''","'")
						dataContent=dataContent.replace("'","''")
						removequery="UPDATE {} SET data=\'{}\' where pkg=\'{}\'".format(tmpdb,dataContent,alias)
						cursor.execute(removequery)
						db.commit()
				queryMany="INSERT or REPLACE INTO {} VALUES (?,?,?,?,?,?)".format(tmpdb)
				try:
					cursor.executemany(queryMany,query)
					db.commit()
				except Exception as e:
					self._debug(e)
					#self._debug(query)
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

	def _addPkgToQuery(self,table,cursor,data,restricted=True):
		(cat0,cat1,cat2)=(None,None,None)
		processedpkg=([],[])
		aliaspkg=([],[])
		(pkgname,pkgdata)=data
		pkgdataJson=json.loads(pkgdata)
		self.filters=False
		if self.filters:
			banList=self._applyFilters(pkgname,pkgdataJson)
			if banList==True:
				return(processedpkg)
		query="pkg='{0}' or alias = '{0}'".format(pkgname)
		fetchquery="SELECT * FROM {0} WHERE {1}".format(table,query)
		row=cursor.execute(fetchquery).fetchone()
		if not(row):
			bypkgalias=False
			query="pkg = '{0}'".format(pkgname)
			fetchquery="SELECT * FROM {0} WHERE {1}".format(table,query)
			row=cursor.execute(fetchquery).fetchone()
		if row:
			rowname=row[0]
			if rowname!=pkgname: #Alias
				alias=row[0]
				aliasdata=json.loads(row[1])
				aliaspkgdataJson=pkgdataJson.copy()
				aliaspkgdataJson["name"]=alias
				aliasname=""
				if "Zomando" not in aliaspkgdataJson.get("categories"):
					aliasname=aliasdata["name"]
				aliasdesc=""
				#rejected eduapps needs webscrap of detail url
				#for the moment it's disabled because is time-consuming
				#However when the info gets loaded this should work
				if "Forbidden" in aliasdata["categories"]:
					aliasdesc=aliasdata["description"]
				aliaspkgdataJson=self._mergePackage(aliaspkgdataJson,row)
				if len(aliasdesc)>0:
					if aliasdesc!=aliaspkgdataJson["description"]:
						aliaspkgdataJson["description"]=aliasdesc
			
				elif len(aliasname)>0:
					aliaspkgdataJson["name"]=pkgname
				aliaspkg=self._processPkgData(alias,aliaspkgdataJson)
				query="pkg = '{0}'".format(pkgname)
				fetchquery="SELECT * FROM {0} WHERE {1}".format(table,query)
				row=cursor.execute(fetchquery).fetchone()
			if row:
				pkgdataJson=self._mergePackage(pkgdataJson,row)
			if len(pkgdataJson.get('bundle',{}))>0:
				processedpkg=self._processPkgData(pkgname,pkgdataJson)
		elif restricted==False:
			if len(pkgdataJson.get('bundle',{}))>0:
				processedpkg=self._processPkgData(pkgname,pkgdataJson)

		return(processedpkg,aliaspkg)
	#def _addPkgToQuery

	def _applyFilters(self,pkgname,pkgdataJson):
		banList=False
		if self.banlist==True:
			banList=self._checkBanList(pkgname,pkgdataJson)
		if self.includelist==True:
			banList=not(self._checkIncludeList(pkgname,pkgdataJson,banList))
		if banList==False:
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
						banList=True
						break
		return(banList)
	 #def _applyFilters

	def _checkBanList(self,pkgname,data,banList=False):
		filtersBan=self.banlistFilter.get('banlist',{})
		categorySet=list(set(data.get('categories',[])))
		filterBanCats=list(set(filtersBan.get('categories',[])))
		#REM: len==len(set) -> no matching categories
		if len(filterBanCats+categorySet)!=len(set(filterBanCats+categorySet)):
			banList=True
		filterBanApps=filtersBan.get('apps',[]) 
		filterBanGlobs=[ c for c in filterBanApps if "*" in c]
		filtersBanApps=[ c for c in filterBanApps if not "*" in c]
		if banList==False:
			if pkgname in filterBanApps:
				banList=True
			else:
				for glob in filterBanGlobs:
					if pkgname.startswith(glob.replace("*","")):
						banList=True
					elif pkgname.endswith(glob.replace("*","")):
						banList=True
		return(banList)
	#def _checkBanList

	def _checkIncludeList(self,pkgname,data,banList=False):
		includeList=False
		categorySet=list(set(data.get('categories',[])))
		filterInclude=self.includelistFilter.get('includelist',{})
		filterBan=self.includelistFilter.get('banlist',{})
		filterIncludeCats=list(set(filterInclude.get('categories',[])))
		filterIncludeApps=filterInclude.get('apps',[]) 
		filterIncludeGlobs=[ c for c in filterIncludeApps if "*" in c]
		filterIncludeApps=[ c for c in filterIncludeApps if not "*" in c]
		if len(filterIncludeApps+filterIncludeGlobs)==0 and len(filterIncludeCats)==0:
			includeList=not(banList)
		else:
			if pkgname in filterIncludeApps:
				includeList=True
			else:
				for glob in filterIncludeGlobs:
					if pkgname.startswith(glob.replace("*","")):
						includeList=True
						break
					elif pkgname.endswith(glob.replace("*","")):
						includeList=True
						break
			if len(filterIncludeCats)>0 and includeList==False and banList==False:
				if len(filterIncludeCats+categorySet)!=len(set(filterIncludeCats+categorySet)):
					includeList=True
		return(includeList)
	#def _checkIncludeList

	def _processPkgData(self,pkgname,pkgdataJson):
	#REM This code removes a candidate zmd package with no zomando associated
		if pkgname.startswith("zero-"):
			if len(pkgdataJson.get("bundle",{}).get("zomando",""))==0:
				self._debug("DISCARD {}".format(pkgname))
				return([],[])
		categories=pkgdataJson.get('categories',[]).copy()
		if "Forbidden" in categories:
			self._debug("Set app {} as Forbidden".format(pkgname))
			categories.remove("Forbidden")
			categories.insert(0,"Forbidden")
			for item in pkgdataJson.get("bundle",""):
				item=""
		elif "Lliurex" in categories:
			idx=categories.index("Lliurex")
			if idx!=0:
				pkgdataJson['categories'].pop(idx)
				pkgdataJson['categories'].insert(0,categories[idx])
			categories=pkgdataJson.get('categories',[])
		noShowCategories=["GTK","QT","Qt","Kde","KDE","Java","Gnome","GNOME","desktop-other"]
		categories=list(set(categories)-set(noShowCategories))
			
		while len(categories)<3:
			categories.append("")
		if ("Lliurex" in categories):
			cat0="Lliurex"
			cat1=categories[1]
			cat2=categories[-1]
		else:
			cat0=categories[0]
			cat1=categories[-1]
			cat2=categories[-2]
		if "Zomando" in categories and "Zomando" not in cat0+cat1+cat2:
			cat2="Zomando"
		if "FP" in categories and "FP" not in cat0+cat1+cat2:
			cat1="FP"
		if isinstance(pkgdataJson['versions'],dict):
			states=pkgdataJson.get('state')
			#pkgdataJson['installed']={}
			for bun,state in states.items():
				if state=="0":
					if bun not in pkgdataJson["installed"].keys():
						pkgdataJson['installed'][bun]=pkgdataJson.get('versions',{}).get(bun,0)
				else:
					if bun in pkgdataJson["installed"].keys():
						pkgdataJson["installed"].pop(bun)

		pkgdataJson['description']=rebostHelper._sanitizeString(pkgdataJson['description'],unescape=True)
		pkgdataJson['summary']=rebostHelper._sanitizeString(pkgdataJson['summary'])
		pkgdataJson['name']=rebostHelper._sanitizeString(pkgdataJson['name'])
		alias=pkgdataJson.get("alias","")
		pkgdata=str(json.dumps(pkgdataJson))
		return([pkgname,pkgdata,cat0,cat1,cat2,alias],categories)
	#def _processPkgData

	def _mergePackage(self,pkgdataJson,row):
		(pkg,data,cat0,cat1,cat2,alias)=row
		mergepkgdataJson=json.loads(data)
		eduapp=mergepkgdataJson.get("bundle",{}).get("eduapp","")
		eduappSum=""
		if len(eduapp)>0:
			eduappSum=mergepkgdataJson.get("summary","")
			mergepkgdataJson["bundle"].pop("eduapp")
			if "eduapp" in mergepkgdataJson["versions"]:
				mergepkgdataJson["versions"].pop("eduapp")
		print(eduappSum)
		mergepkgdataJson=self._mergeData(pkgdataJson,mergepkgdataJson)
		#If package comes from eduapps and is not maped then
		#appstream adds a bundle "eduapps". Replace it as if there's info
		#in appstream then this pkg is available from repos
		eduapp=mergepkgdataJson.get("bundle",{}).get("eduapp","")
		eduappv=mergepkgdataJson.get("versions",{}).get("eduapp","")
		if len(eduapp)>0:
			mergepkgdataJson["bundle"]={"package":eduapp}
			mergepkgdataJson["versions"]={"package":eduappv}
		if len(eduappSum)>0:
			mergepkgdataJson["summary"]="{} ({})".format(mergepkgdataJson["summary"],eduappSum)
		return(mergepkgdataJson)
	#def _mergePackage

	def _mergeData(self,pkgdataJson,mergepkgdataJson):
		for key,item in pkgdataJson.items():
			if not key in mergepkgdataJson.keys():
				mergepkgdataJson[key]=item
			elif isinstance(item,dict) and isinstance(mergepkgdataJson.get(key,''),dict):
				if len(item)>0 and "eduapps" not in item.keys():
					mergepkgdataJson[key].update(item)
			elif isinstance(item,list) and isinstance(mergepkgdataJson.get(key,''),list):
				if len(item)>0:
					mergepkgdataJson[key].extend(item)
					tmp=[]
					for i in list(set(mergepkgdataJson[key])):
						if i:
							tmp.append(i)
					mergepkgdataJson[key]=tmp
			elif isinstance(item,str) and isinstance(mergepkgdataJson.get(key,None),str):
				#If icon exists use it
				if len(item)>=len(mergepkgdataJson.get(key,'')):
					mergepkgdataJson[key]=item
		return(mergepkgdataJson)
	#def _mergeData

	def _generateCompletion(self):
		table=os.path.basename(self.main_table).replace(".db","")
		(db,cursor)=self.enableConnection(self.main_table,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
		query="SELECT pkg FROM {};".format(table)
		cursor.execute(query)
		rows=cursor.fetchall()
		completionFile=os.path.join(self.rebostCache,"tmp","bash_completion")
		if os.path.isdir(os.path.dirname(completionFile)):
			with open(completionFile,'w') as f:
				for row in rows:
					f.write("{}\n".format(row[0]))
		self.closeConnection(db)
	#def _generateCompletion

	def _chkNeedUpdate(self):
		update=False
		include=["eduapps.db","appimage.db","flatpak.db","snap.db","zomandos.db","appstream.db"]
		if os.path.isfile(self.lastUpdate)==False:
			if os.path.isdir(os.path.dirname(self.lastUpdate))==False:
				os.makedirs(os.path.dirname(self.lastUpdate))
			update=True
		else:
			with open(self.lastUpdate,'r') as f:
				fcontent=f.readlines()
			for fname in include:
				f=os.path.join(self.rebostCache,fname)
				fsize=0
				if os.path.isfile(f):
					fsize=os.path.getsize(f)
				for f in fcontent:
					if fname.split(".")[0] in f:
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
		(db,cursor)=self.enableConnection(f,["cat0 TEXT","cat1 TEXT","cat2 TEXT","alias TEXT"])
		query="SELECT pkg,data FROM {}".format(table)
		cursor.execute(query)
		allData=cursor.fetchall()
		self.closeConnection(db)
		return (allData)
	#def _getAllData

	def copyBaseTable(self,consolidate_table):
		rebost_db=sqlite3.connect(self.main_tmp_table)
		cursor=rebost_db.cursor()
		table=os.path.basename(self.main_table).replace(".db","")
		query="DROP TABLE IF EXISTS {}".format(table)
		cursor.execute(query)
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT, cat0 TEXT, cat1 TEXT, cat2 TEXT,alias TEXT);".format(table)
		cursor.execute(query)
		cursor.execute("ATTACH DATABASE '{}.db' AS pk;".format(os.path.join(self.rebostCache,consolidate_table)))
		cursor.execute("INSERT INTO {0} (pkg,data,cat0,cat1,cat2,alias) SELECT * from pk.{1};".format(table,consolidate_table))
		rebost_db.commit()
		rebost_db.close()
	#def copyBaseTable

	def _copyTmpDef(self):
		#Copy tmp to definitive
		if os.path.isfile(self.main_tmp_table):
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

