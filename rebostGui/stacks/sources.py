#!/usr/bin/python3
import sys
import os,subprocess
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
	"RELOAD":_("Reload catalogues")
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
	#def __init__

	def _load_screen(self):
		self.config=self.getConfig()
		print(self.config)
		self.box=QGridLayout()
		icn=QtGui.QIcon.fromTheme("go-previous")
		self.btnBack=QPushButton()
		self.btnBack.setIcon(icn)
		self.btnBack.clicked.connect(self._return)
		self.btnBack.setIconSize(QSize(48,48))
		self.btnBack.setFixedSize(QSize(64,64))
		self.box.addWidget(self.btnBack,0,0,1,1,Qt.AlignTop)
		self.chkApt=QCheckBox("Apt source")
		self.box.addWidget(self.chkApt,1,0,1,1,Qt.AlignCenter)
		self.chkSnap=QCheckBox("Snap source")
		self.box.addWidget(self.chkSnap,2,0,1,1,Qt.AlignCenter)
		self.chkFlatpak=QCheckBox("Flatpak source")
		self.box.addWidget(self.chkFlatpak,3,0,1,1,Qt.AlignCenter)
		self.chkImage=QCheckBox("AppImage source")
		self.box.addWidget(self.chkImage,4,0,1,1,Qt.AlignCenter)
		btnReload=QPushButton(i18n.get("RELOAD"))
		btnReload.clicked.connect(self._reloadCatalogue)
		self.box.addWidget(btnReload,5,0,1,1,Qt.AlignCenter)
		self.setLayout(self.box)
	#def _load_screen

	def _reloadCatalogue(self):
		cmd=["service","rebost","restart"]
		subprocess.run(cmd)
	#def _reloadCatalogue

	def _return(self):
		self.stack.gotoStack(idx=1,parms="")

	def updateScreen(self):
		pass
	#def _udpate_screen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		self.saveChanges('config','user',level='user')
		for wdg in [self.chkSnap,self.chkFlatpak,self.chkApt,self.chkImage]:
			key=wdg.text().split(" ")[0].lower()
			data=wdg.isChecked()
			self.saveChanges(key,data,level=self.level)
		return

