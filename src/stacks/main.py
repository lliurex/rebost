#!/usr/bin/python3
import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QVBoxLayout,QLineEdit,QGridLayout,QHBoxLayout,QComboBox,QCheckBox,QTableWidget, \
				QGraphicsDropShadowEffect, QHeaderView
from PyQt5 import QtGui
from PyQt5.QtCore import Qt,QSize,pyqtSignal
from appconfig.appConfigStack import appConfigStack as confStack
from edupals.ui import QAnimatedStatusBar
from app2menu import App2Menu

import gettext
_ = gettext.gettext

class main(confStack):
	def __init_stack__(self):
		self.dbg=False
		self._debug("main load")
		self.description=(_("Rebost"))
		self.menu_description=(_("Manage software"))
		self.icon=('dialog-password')
		self.tooltip=(_("From here you can manage the software available on your system"))
		self.index=1
		self.enabled=True
		self.level='system'
		self.hideControlButtons()
		self.menu=App2Menu.app2menu()
		self.setStyleSheet(self._setCss())
		self.widget=''
		self.paths=["/usr/local/bin","%s/AppImages"%os.environ["HOME"],"%s/Applications"%os.environ["HOME"]]
	#def __init__
	
	def _load_screen(self):
		box=QVBoxLayout()
		self.setLayout(box)
		self.updateScreen()
		return(self)
	#def _load_screen

	def updateScreen(self):
		return True
	#def _udpate_screen

	def writeConfig(self):
		if self.widget=='':
			return
		self.appmanager.localRemove(self.widget.getApp())
		self.showMsg(_("App %s uninstalled"%self.widget.getName()))
		self.updateScreen()
	#def writeConfig

	def _setCss(self):
		css="""
		#cell{
			padding:10px;
			margin:6px;
			background-color:rgb(250,250,250);

		}
		#appName{
			font-weight:bold;
			border:0px;
		}
		#btnRemove{
			background:red;
			color:white;
			font-size:9pt;
			padding:3px;
			margin:3px;
		}
		
		"""

		return(css)
	#def _setCss

