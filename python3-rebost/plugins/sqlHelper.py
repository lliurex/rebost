#!/usr/bin/env python3
import os
import gi
from gi.repository import Gio
import json
import rebostHelper
import logging
import html
import sqlite3
from shutil import copyfile

class sqlHelper():
	def __init__(self,*args,**kwargs):
		self.dbg=True
		logging.basicConfig(format='%(message)s')
		self.enabled=True
		self.actions=["show","search","load"]
		self.packagekind="*"
		self.priority=100
		self.postAutostartActions=["load"]
		self.store=None
		self.progressQ={}
		self.progress={}
		self.resultQ={}
		self.result={}
		self.main_table="rebostStore.db"
		self.main_tmp_table="tmpStore.db"
		#self.consolidate_sql_tables()

	def setDebugEnabled(self,enable=True):
		self._debug("Debug %s"%enable)
		self.dbg=enable
		self._debug("Debug %s"%self.dbg)

	def _debug(self,msg):
		if self.dbg:
			logging.warning("sql: %s"%str(msg))

	def _on_error(self,action,e):
		self.progressQ[action].put(100)
		self.resultQ[action].put(str(json.dumps([{'name':action,'description':'Error','error':"1",'errormsg':str(e)}])))

	#def execute(self,action,*args):
	def execute(self,procId,action,progress,result,store,args=''):
		self._debug(action)
		rs=''
		if action=='search':
			rs=self._searchPackage(args)
		if action=='show':
			rs=self._showPackage(args)
		if action=='load':
			rs=self.consolidate_sql_tables()
		return(rs)

	def execute2(self,procId,action,progress,result,store,args=''):
		self.procId=procId
		if action in self.actions:
			self.progressQ[action]=progress
			self.resultQ[action]=result
			self.progress[action]=0
			if action=='search':
				self._searchStore(args)

	def _showPackage(self,pkgname):
		table=self.main_table.replace(".db","")
		(db,cursor)=self.enable_connection(self.main_table)
		query="SELECT * FROM {} WHERE pkg LIKE '{}' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		return(rows)

	def _searchPackage(self,pkgname):
		table=self.main_table.replace(".db","")
		(db,cursor)=self.enable_connection(self.main_table)
		query="SELECT * FROM {} WHERE pkg LIKE '%{}%' ORDER BY INSTR(pkg,'{}'), '{}'".format(table,pkgname,pkgname,pkgname)
		#self._debug(query)
		cursor.execute(query)
		rows=cursor.fetchall()
		return(rows)

	def enable_connection(self,table):
		db=sqlite3.connect(table)
		cursor=db.cursor()
		table=table.replace(".db","")
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(table)
		cursor.execute(query)
		return(db,cursor)

	def close_connection(self,db):
		db.commit()
		db.close()

	def consolidate_sql_tables(self):
		self._debug("Merging data")
		main_db=sqlite3.connect(self.main_tmp_table)
		main_tmp_table=self.main_table.replace(".db","")
		main_cursor=main_db.cursor()
		query="CREATE TABLE IF NOT EXISTS {} (pkg TEXT PRIMARY KEY,data TEXT);".format(main_tmp_table)
		main_cursor.execute(query)
		exclude=[self.main_tmp_table,self.main_table,"packagekit.db"]
		self.copy_packagekit_sql()
		for f in os.listdir("."):
			if f.endswith(".db") and f not in exclude:
				table=f.replace(".db","")
				self._debug("Accesing {}".format(f))
				(db,cursor)=self.enable_connection(f)
				query="SELECT * FROM {}".format(table)
				cursor.execute(query)
				for data in cursor.fetchall():
					(key,value)=data
					json_value=json.loads(value)
					query="SELECT * FROM {} WHERE pkg LIKE '{}'".format(main_tmp_table,key)
					rows=main_cursor.execute(query).fetchone()
					if rows:
						#self._debug("Update pkg {}".format(key))
						(main_key,main_data)=rows
						if main_data:
							json_main_value=json.loads(main_data)
							if json_value.get('bundle') and json_value.get('bundle')!=json_main_value.get('bundle'):
								#json_main_value['bundle'][table]=json_value['bundle']
								json_main_value['bundle'].update(json_value['bundle'])
								value=str(json.dumps(json_main_value))
								#self._debug(value)
							if json_value.get('versions') and json_value.get('versions')!=json_main_value.get('versions'):
								json_main_value['versions'].update(json_value['versions'])
								value=str(json.dumps(json_main_value))
					query="INSERT INTO {} (pkg, data) VALUES ('{}', '{}') ON CONFLICT(pkg) DO UPDATE SET data='{}';".format(main_tmp_table,key,value,value)
					#self._debug(query)
					main_cursor.execute(query)
				self.close_connection(db)
		main_db.commit()
		main_db.close()
		#Copy tmp to definitive
		self._debug("Copying main table")
		copyfile(self.main_tmp_table,self.main_table)
		self._debug("Removing tmp file")
		os.remove(self.main_tmp_table)
		return([])

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

def main():
	obj=sqlHelper()
	return (obj)

