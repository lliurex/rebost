#!/usr/bin/python3
import sys
import os,subprocess,time,shutil
from PySide2.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QGridLayout,QTableWidget,QHeaderView,QHBoxLayout,QCheckBox
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSignalMapper,QSize,QThread,Signal
#from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appConfig
from QtExtraWidgets import QStackedWindowItem
from rebost import store
import json
import random
import gettext
_ = gettext.gettext
QString=type("")

i18n={
	"CONFIG":_("Sources"),
	"DESC":_("Show software sources"),
	"MENU":_("Configure software sources"),
	"TOOLTIP":_(""),
	"RELOAD":_("Reload catalogues"),
	"RELOAD_TOOLTIP":_("Reload info from sources"),
	"CCACHE":_("Clear cache"),
	"CCACHE_TOOLTIP":_("Remove all files from cache, as per exemple icons or another related stuff"),
	"RESET":_("Restart database"),
	"RESET_TOOLTIP":_("Forces a refresh of all the info from sources resetting all previous stored information"),
	"RESTARTFAILED":_("Service could not be reloaded. Check credentials"),
	"SOURCE_FP":_("Include flatpaks"),
	"SOURCE_SN":_("Include snaps"),
	"SOURCE_AI":_("Include appimages"),
	"SOURCE_PK":_("Include native packages")
	}

class reloadCatalogue(QThread):
	active=Signal()
	def __init__(self,rc,force,parent=None):
		QThread.__init__(self,parent)
		self.rc=rc
		self.force=force
	#def __init__

	def run(self):
		try:
			self.rc.update(force=self.force)
		except:
			time.sleep(1)
			self.rc.update(force=self.force)
		self.active.emit()
	#def run
#class reloadCatalogue

class setWaiting(QThread):
	def __init__(self,widget,parent=None):
		self.widget=widget
		if parent==None:
			self.parent=parent
		self.oldcursor=widget.cursor()
	#def __init__

	def run(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.widget.setCursor(cursor)
		
		for wdg in self.widget.findChildren(QPushButton):
			wdg.setEnabled(False)
		for wdg in self.widget.findChildren(QCheckBox):
			wdg.setEnabled(False)
		QApplication.processEvents()
		return(True)
	#def run
	
	def stop(self):
		for wdg in self.widget.findChildren(QPushButton):
			wdg.setEnabled(True)
		for wdg in self.widget.findChildren(QCheckBox):
			wdg.setEnabled(True)
		self.widget.setCursor(self.oldcursor)
	#def stop
#class setWaiting
	
class sources(QStackedWindowItem):
	def __init_stack__(self):
		self.dbg=False
		self._debug("sources load")
		self.setProps(shortDesc=i18n.get("MENU"),
			longDesc=i18n.get("DESC"),
			icon="application-x-desktop",
			tooltip=i18n.get("TOOLTIP"),
			index=2,
			visible=True)
		self.index=2
		self.enabled=True
		self.visible=False
		self.rc=store.client()
		self.appconfig=appConfig.appConfig()
		self.appconfig.setConfig(confDirs={'system':os.path.join('/usr/share',"rebost"),'user':os.path.join(os.environ['HOME'],'.config',"rebost")},confFile="store.json")
		self.changed=[]
		self.config={}
		self.app={}
		self.level='system'
		self.oldcursor=self.cursor()
	#def __init__

	def __initScreen__(self):
		self.box=QGridLayout()
		icn=QtGui.QIcon.fromTheme("go-previous")
		self.btnBack=QPushButton()
		self.btnBack.setIcon(icn)
		self.btnBack.clicked.connect(self._return)
		self.btnBack.setIconSize(QSize(48,48))
		self.btnBack.setFixedSize(QSize(64,64))
		self.box.addWidget(self.btnBack,0,0,1,1,Qt.AlignTop)
		self.chkApt=QCheckBox(i18n.get("SOURCE_PK"))
		self.box.addWidget(self.chkApt,4,1,1,1,Qt.AlignLeft)
		self.chkSnap=QCheckBox(i18n.get("SOURCE_SN"))
		if shutil.which("snap")==None:
			self.chkSnap.setEnabled(False)
		self.box.addWidget(self.chkSnap,1,1,1,1,Qt.AlignLeft)
		self.chkFlatpak=QCheckBox(i18n.get("SOURCE_FP"))
		if shutil.which("flatpak")==None:
			self.chkFlatpak.setEnabled(False)
		self.box.addWidget(self.chkFlatpak,2,1,1,1,Qt.AlignLeft)
		self.chkImage=QCheckBox(i18n.get("SOURCE_AI"))
		self.box.addWidget(self.chkImage,3,1,1,1,Qt.AlignLeft)
		btnClear=QPushButton(i18n.get("CCACHE"))
		btnClear.setToolTip(i18n.get("CCACHE_TOOLTIP"))
		btnClear.clicked.connect(self._clearCache)
		self.box.addWidget(btnClear,1,2,1,1)
		btnReload=QPushButton(i18n.get("RELOAD"))
		btnReload.setToolTip(i18n.get("RELOAD_TOOLTIP"))
		btnReload.clicked.connect(self._reload)
		self.box.addWidget(btnReload,2,2,1,1)
		btnReset=QPushButton(i18n.get("RESET"))
		btnReset.setToolTip(i18n.get("RESET_TOOLTIP"))
		btnReset.clicked.connect(lambda x:self._resetDB(True))
		self.box.addWidget(btnReset,3,2,1,1)
		self.box.setRowStretch(self.box.rowCount(), 1)
		self.setLayout(self.box)
		self.btnAccept.clicked.connect(self.writeConfig)
	#def _load_screen

	def _clearCache(self):
		cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		self._setEnabled(False)
		if os.path.isdir(cacheDir):
			try:
				shutil.rmtree(cacheDir)
			except Exception as e:
				print("Error removing {0}: {1}".format(cacheDir,e))
		self._setEnabled(True)
	#def _clearCache

	def _setEnabled(self,state):
		if state==False:
			cursor=QtGui.QCursor(Qt.WaitCursor)
			self.setCursor(cursor)
		else:
			self.setCursor(self.oldcursor)
		QApplication.processEvents()
		for wdg in self.findChildren(QPushButton):
			wdg.setEnabled(state)
		for wdg in self.findChildren(QCheckBox):
			wdg.setEnabled(state)
		QApplication.processEvents()
	#def _setEnabled

	def _resetDB(self,refresh=False):
		if refresh==True:
			if self.changes:
				self.writeConfig()
		self.btnBack.clicked.connect(self.btnBack.text)
		self.changes=False
		self._setEnabled(False)
		self._reloadCatalogue(True)
		self._setEnabled(True)
	#def _resetDB

	def _reload(self):
		self.btnBack.clicked.connect(self.btnBack.text)
		self._setEnabled(False)
		self._reloadCatalogue(False)
		self._setEnabled(True)
	#def _reload
		
	def _reloadCatalogue(self,force=False):
		reloadRebost=reloadCatalogue(self.rc,force)
		if self.changes:
			self.writeConfig()
		reloadRebost.active.connect(self._endReloadCatalogue)
		reloadRebost.run()
	#def _reloadCatalogue

	def _endReloadCatalogue(self):
		print("****")
		self.rc=None
		try:
			self.rc=store.client()
		except:
			time.sleep(1)
			try:
				self.rc=store.client()
			except:
				print("UNKNOWN ERROR")
		time.sleep(2)
		self.updateScreen()
	#def _endreloadCatalogue

	def _return(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		self.parent.setCurrentStack(1,parms="1")
		self.setCursor(self.oldcursor)
	#def _return

	def updateScreen(self):
		self.changes=True
		self.refresh=True
		self.config=self.appconfig.getConfig()
		self.chkSnap.setChecked(True)
		self.chkFlatpak.setChecked(True)
		self.chkImage.setChecked(True)
		for key,value in self.config.get(self.level,{}).items():
			if key=="packageKit":
				self.chkApt.setChecked(value)
			if key=="snap":
				self.chkSnap.setChecked(value)
			if key=="flatpak":
				self.chkFlatpak.setChecked(value)
			if key=="appimage":
				self.chkImage.setChecked(value)
	#def _udpate_screen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		self.appconfig.level="system"
		self.appconfig.saveChanges('config','system',level='system')
		for wdg in [self.chkSnap,self.chkFlatpak,self.chkApt,self.chkImage]:
			key=""
			if wdg==self.chkApt:
				key="packageKit"
			elif wdg==self.chkFlatpak:
				key="flatpak"
			elif wdg==self.chkImage:
				key="appimage"
			elif wdg==self.chkSnap:
				key="snap"
			data=wdg.isChecked()
			if len(key)>0:
				self.appconfig.saveChanges(key,data,level=self.level)
		self._resetDB()
	#def writeConfig

