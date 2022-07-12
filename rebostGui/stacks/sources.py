#!/usr/bin/python3
import sys
import os,subprocess,time,shutil
from PySide2.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QGridLayout,QTableWidget,QHeaderView,QHBoxLayout,QCheckBox
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSignalMapper,QSize
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appconfigControls
from rebost import store
import json
import random
import gettext
_ = gettext.gettext
QString=type("")

i18n={
	"CONFIG":_("Sources"),
	"DESCRIPTION":_("Show software sources"),
	"MENUDESCRIPTION":_("Configure software sources"),
	"TOOLTIP":_(""),
	"RELOAD":_("Reload catalogues"),
	"CCACHE":_("Clear cache"),
	"RESTARTFAILED":_("Service could not be reloaded. Check credentials")
	}

class sources(confStack):
	def __init_stack__(self):
		self.dbg=True
		self._debug("details load")
		self.menu_description=i18n.get('MENUDESCRIPTION')
		self.description=i18n.get('DESCRIPTION')
		self.icon=('application-x-desktop')
		self.tooltip=i18n.get('TOOLTIP')
		self.index=2
		self.enabled=True
		self.visible=False
		self.rc=store.client()
		self.changed=[]
		self.config={}
		self.app={}
		self.level='system'
	#def __init__

	def _load_screen(self):
		self.box=QGridLayout()
		icn=QtGui.QIcon.fromTheme("go-previous")
		self.btnBack=QPushButton()
		self.btnBack.setIcon(icn)
		self.btnBack.clicked.connect(self._return)
		self.btnBack.setIconSize(QSize(48,48))
		self.btnBack.setFixedSize(QSize(64,64))
		self.box.addWidget(self.btnBack,0,0,1,1,Qt.AlignTop)
		self.chkApt=QCheckBox("Apt source")
		self.chkApt.setEnabled(False)
		self.box.addWidget(self.chkApt,1,1,1,1,Qt.AlignCenter|Qt.AlignCenter)
		self.chkSnap=QCheckBox("Snap source")
		self.box.addWidget(self.chkSnap,2,1,1,1,Qt.AlignCenter|Qt.AlignCenter)
		self.chkFlatpak=QCheckBox("Flatpak source")
		self.box.addWidget(self.chkFlatpak,1,2,1,1,Qt.AlignCenter|Qt.AlignCenter)
		self.chkImage=QCheckBox("AppImage source")
		self.box.addWidget(self.chkImage,2,2,1,1,Qt.AlignCenter|Qt.AlignCenter)
		btnReload=QPushButton(i18n.get("RELOAD"))
		btnReload.clicked.connect(self._reloadCatalogue)
		self.box.addWidget(btnReload,3,1,1,1,Qt.AlignRight|Qt.AlignCenter)
		btnClear=QPushButton(i18n.get("CCACHE"))
		btnClear.clicked.connect(self._clearCache)
		self.box.addWidget(btnClear,3,2,1,1,Qt.AlignLeft|Qt.AlignCenter)
		self.setLayout(self.box)
	#def _load_screen

	def _clearCache(self):
		cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		try:
			shutil.rmtree(cacheDir)
		except Exception as e:
			print("Error removing {0}: {1}".format(cacheDir,e))
	#def _clearCache

	def _reloadCatalogue(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		if self.changes:
			self.writeConfig()
		cmd=["service","rebost","restart"]
		res=subprocess.run(cmd)
		if res.returncode!=0:
			self.showMsg(i18n.get("RESTARTFAILED"))
		else:
			self.grabMouse()
			cursor=QtGui.QCursor(Qt.WaitCursor)
			self.setCursor(cursor)
			time.sleep(5)
			self.rc.searchApp("firefox")
			self.releaseMouse()
		cursor=QtGui.QCursor(Qt.PointingHandCursor)
		self.setCursor(cursor)
	#def _reloadCatalogue

	def _return(self):
		self.stack.gotoStack(idx=1,parms="1")
	#def _return

	def updateScreen(self):
		self.changes=True
		self.config=self.getConfig()
		for key,value in self.config.get(self.level,{}).items():
			if key=="apt":
				self.chkApt.setChecked(True)
			if key=="snap":
				self.chkSnap.setChecked(value)
			if key=="flatpak":
				self.chkFlatpak.setChecked(value)
			if key=="appimage":
				self.chkImage.setChecked(value)
		pass
	#def _udpate_screen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		self.level="system"
		self.saveChanges('config','system',level='system')
		for wdg in [self.chkSnap,self.chkFlatpak,self.chkApt,self.chkImage]:
			key=wdg.text().split(" ")[0].lower()
			data=wdg.isChecked()
			self.saveChanges(key,data,level=self.level)
		return

