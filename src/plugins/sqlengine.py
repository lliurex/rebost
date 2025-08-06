#!/usr/bin/python3
import sys,os
import json
import sqlite3

#Constants

class engine:
	def __init__(self,core,*args,**kwargs):
		self.core=core
		self.dbg=self.core.DBG
	#self __init__
	
	def _debug(self,msg):
		if self.dbg==True:
			print("engine: {}".format(msg))
	#self _debug

	def _getAvailableTables(self):
		tables=[]
		fsql=os.path.join(self.core.DBDIR,"rebost.db")
		if os.path.exists(fsql):
			db=sqlite3.connect(fsql)
			cursor=db.cursor()
			query=("SELECT name FROM sqlite_master WHERE type='table';")
			rows=cursor.execute(query).fetchall()
			tables=[table[0] for table in rows]
		return(tables)
	#def _getAvailableDb

	def _getSupportedFormats(self):
		bundles=[]
		for bundle in self.core.supportedformats:
			if bundle==self.core.appstream.BundleKind.APPIMAGE:
				bundles.append("appimage")
			elif bundle==self.core.appstream.BundleKind.SNAP:
				bundles.append("snap")
			elif bundle==self.core.appstream.BundleKind.FLATPAK:
				bundles.append("flatpak")
			elif bundle==self.core.appstream.BundleKind.PACKAGE:
				bundles.append("package")
			else:
				bundles.append("other")
		return(bundles)
	#def _getSchemes

	def _schemeForDb(self,db,schemes):
		if "{}.sql".format(db) in schemes:
			scheme=os.path.join(self.core.SCHEMES,"{}.sql".format(db))
		else:
			scheme=os.path.join(self.core.SCHEMES,"default.sql")
		return(scheme)
	#def _dbFromScheme

	def _createDatabases(self,databases):
		self._debug("Populating data structure")
		schemes=[]
		if os.path.exists(self.core.SCHEMES):
			schemes=os.listdir(self.core.SCHEMES)
		for db in databases:
			scheme=self._schemeForDb(db,schemes)
			if os.path.exists(scheme):
				with open(scheme,"r") as f:
					sql=f.read()
				sql=sql.replace("{TABLENAME}",db)
				fsql=os.path.join(self.core.DBDIR,"rebost.db")
				db=sqlite3.connect(fsql)
				cursor=db.cursor()
				cursor.execute(sql)
	#def _createDatabases

	def chkDatabases(self):
		tables=self._getAvailableTables()
		tables=[tb.replace(".db","") for tb in tables] 
		pending=[]
		bundles=self._getSupportedFormats()
		if (len(tables)==0) and not(os.path.exists(self.core.DBDIR)):
			os.makedirs(self.core.DBDIR)
		if len(tables+bundles)!=0:
			pending=list(set(bundles)-set(tables))
			if len(pending)>0:
				self._debug("Table discrepancy ({})".format(pending))
				self._createDatabases(pending)
				tables=self._getAvailableTables()
		self._debug("Engine operative ({})".format(len(tables)))
		return(tables)
	#def chkDatabases
#class engine
