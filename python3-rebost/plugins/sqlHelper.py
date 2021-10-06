#!/usr/bin/env python3
import os
import gi
from gi.repository import Gio
import json
import rebostHelper
import logging
import html
import sqlite3
import subprocess
from shutil import copyfile
import time
import appimageHelper

class sqlHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.gui=False
		self.actions=["show","search","load",'commitInstall']
		self.packagekind="*"
		self.priority=100
		self.postAutostartActions=["load"]
		self.store=None
		self.main_table="rebostStore.db"
		self.proc_table="rebostPrc.db"
		self.main_tmp_table="tmpStore.db"
		if os.path.isfile(self.main_tmp_table):
			os.remove(self.main_tmp_table)
		self.appimage=appimageHelper.appimageHelper()
	#def __init__

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)
	#def setDebugEnabled

	def _debug(self,msg):
		if self.dbg:
			logging.warning("sql: %s"%str(msg))
	#def _debug

	def execute(self,*args,action='',parms='',extraParms='',extraParms2='',**kwargs):
		self._debug(action)
		rs='[{}]'
		if action=='search':
			rs=self._searchPackage(parms)
		if action=='show':
			rs=self._showPackage(parms)
		if action=='load':
			rs=self.consolidate_sql_tables()
		if action=='commitInstall':
			rs=self._commitInstall(parms,extraParms,extraParms2)
		return(rs)
	#def execute

	def enable_connection(self,table):
		db=sqlite3.connect(table)
		cursor=db.cursor()
		table=table.replace(".db","")
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table)
		cursor.execute(query)
		return(db,cursor)
	#def enable_connection

	def close_connection(self,db):
		db.commit()
		db.close()
	#def close_connection

	def _showPackage(self,pkgname):
		table=self.main_table.replace(".db","")
		(db,cursor)=self.enable_connection(self.main_table)
		query="SELECT * FROM {} WHERE pkg LIKE '{}' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		self._debug(query)
		cursor.execute(query)
		rowsTmp=cursor.fetchall()
		rows=[]
		for row in rowsTmp:
			(pkg,data)=row
			if 'appimage' in json.loads(data).get('bundle',{}).keys():
				if not json.loads(data).get('bundle',{}).get('appimage',',appimage').lower().endswith(".appimage"):
					dataTmp=self.appimage.fillData(data)
					data=dataTmp
					row=(pkg,data)
					query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(table,data,pkgname)
					cursor.execute(query)
					db.commit()
			rows.append(row)
		self.close_connection(db)
		return(rows)
	#def _showPackage

	def _searchPackage(self,pkgname):
		table=self.main_table.replace(".db","")
		(db,cursor)=self.enable_connection(self.main_table)
		query="SELECT * FROM {} WHERE pkg LIKE '%{}%' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		self.close_connection(db)
		return(rows)
	#def _searchPackage

	def _commitInstall(self,pkgname,bundle='',state=0):
		self._debug("Setting status of {} {} as {}".format(pkgname,bundle,state))
		table=self.main_table.replace(".db","")
		(db,cursor)=self.enable_connection(self.main_table)
		query="SELECT * FROM {} WHERE pkg LIKE '{}';".format(table,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		for row in rows:
			(pkg,dataContent)=row
			data=json.loads(dataContent)
			data['state'][bundle]=state

		data['description']=rebostHelper._sanitizeString(data['description'])
		data['summary']=rebostHelper._sanitizeString(data['summary'])
		data['name']=rebostHelper._sanitizeString(data['name'])
		dataContent=json.dumps(data)
		query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(table,dataContent,pkgname)
		self._debug(query)
		cursor.execute(query)
		self.close_connection(db)
		return(rows)
	#def _commitInstall

	def consolidate_sql_tables(self):
		self._debug("Merging data")
		main_db=sqlite3.connect(self.main_tmp_table)
		main_tmp_table=self.main_table.replace(".db","")
		main_cursor=main_db.cursor()
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(main_tmp_table)
		main_cursor.execute(query)
		exclude=[self.main_tmp_table,self.main_table,"packagekit.db",self.proc_table]
		include=["appimage.db","flatpak.db","snap.db"]
		self.copy_packagekit_sql()
		for f in include:
			if os.path.isfile(f) and f not in exclude:
				table=f.replace(".db","")
				self._debug("Accesing {}".format(f))
				(db,cursor)=self.enable_connection(f)
				query="SELECT * FROM {}".format(table)
				cursor.execute(query)
				for data in cursor.fetchall():
					(pkgname,value)=data
					json_value=json.loads(value)
					json_value['description']=rebostHelper._sanitizeString(json_value['description'])
					json_value['summary']=rebostHelper._sanitizeString(json_value['summary'])
					json_value['name']=rebostHelper._sanitizeString(json_value['name'])
					value=str(json.dumps(json_value))
					query="SELECT * FROM {} WHERE pkg LIKE '{}'".format(main_tmp_table,pkgname)
					row=main_cursor.execute(query).fetchone()
					if row:
						(main_key,main_data)=row
						json_main_value=json.loads(main_data).copy()
						for key,item in json_value.items():
							if not key in json_main_value.keys():
								json_main_value[key]=item
							elif isinstance(item,dict) and isinstance(json_main_value.get(key,''),dict):
								json_main_value[key].update(item)
							elif isinstance(item,list) and isinstance(json_main_value.get(key,''),list):
								json_main_value[key].extend(item)
								json_main_value[key] = list(set(json_main_value[key]))
							elif isinstance(item,str) and isinstance(json_main_value.get(key,None),str):
								if len(item)>len(json_main_value.get(key,'')):
									json_main_value[key]=item
						json_main_value['description']=rebostHelper._sanitizeString(json_main_value['description'])
						json_main_value['summary']=rebostHelper._sanitizeString(json_main_value['summary'])
						json_main_value['name']=rebostHelper._sanitizeString(json_main_value['name'])

						value=str(json.dumps(json_main_value))
						query="UPDATE {} SET data='{}' WHERE pkg='{}';".format(main_tmp_table,value,pkgname)
					else:
						query="INSERT INTO {} (pkg, data) VALUES ('{}', '{}');".format(main_tmp_table,pkgname,value,value)
					#self._debug(query)
					try:
						main_cursor.execute(query)
					except Exception as e:
						self._debug(e)
						self._debug(query)
				main_db.commit()
				self.close_connection(db)
		main_db.close()
		#Copy tmp to definitive
		self._debug("Copying main table")
		copyfile(self.main_tmp_table,self.main_table)
		self._debug("Removing tmp file")
		os.remove(self.main_tmp_table)
		return([])
	#def consolidate_sql_tables

	def copy_packagekit_sql(self):
		rebost_db=sqlite3.connect(self.main_tmp_table)
		cursor=rebost_db.cursor()
		table=self.main_table.replace(".db","")
		query="DROP TABLE IF EXISTS {}".format(table)
		cursor.execute(query)
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table)
		cursor.execute(query)
		cursor.execute("ATTACH DATABASE 'packagekit.db' AS pk;")
		cursor.execute("INSERT INTO {} (pkg,data) SELECT * from pk.packagekit;".format(table))
		rebost_db.commit()
		rebost_db.close()
	#def copy_packagekit_sql

def main():
	obj=sqlHelper()
	return (obj)

