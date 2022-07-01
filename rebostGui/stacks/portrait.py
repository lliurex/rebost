#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QGridLayout,QTableWidget,QHeaderView,QHBoxLayout,QComboBox,QLineEdit
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSignalMapper,QSize,QEvent,Signal
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appconfigControls
from rebost import store 
import json
import random
import gettext
_ = gettext.gettext
QString=type("")

i18n={
	"CONFIG":_("Portrait"),
	"DESCRIPTION":_("Show applications"),
	"MENUDESCRIPTION":_("Navigate through all applications"),
	"TOOLTIP":_(""),
	"ALL":_("All")
	}

class QPushButtonRebostApp(QPushButton):
	clicked=Signal("PyObject")
	def __init__(self,strapp,parent=None):
		QPushButton.__init__(self, parent)
		self.app=json.loads(strapp)
		self.setAttribute(Qt.WA_AcceptTouchEvents)
		text="<strong>{0}</strong> - {1}".format(self.app.get('name',''),self.app.get('summary'),'')
		img=self.app.get('icon','')
		self.icon=QLabel()
		icn=''
		if os.path.isfile(img):
			icn=QtGui.QPixmap.fromImage(img)
		elif img=='':
			icn2=QtGui.QIcon.fromTheme('application-x-executable')
			icn=icn2.pixmap(128,128)
		if icn:
			self.icon.setPixmap(icn.scaled(128,128))
		elif img.startswith('http'):
			self.scr=appconfigControls.loadScreenShot(img)
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
		self.label=QLabel(text)
		self.label.setWordWrap(True)
		lay=QHBoxLayout()
		lay.addStretch()
		lay.addWidget(self.icon,0)
		lay.addWidget(self.label,1)
		self.setLayout(lay)
	#def __init__
	
	def load(self,*args):
		img=args[0]
		self.icon.setPixmap(img.scaled(128,128))
	#def load
	
	def activate(self):
		self.clicked.emit(self.app)

	def mousePressEvent(self,*args):
		self.clicked.emit(self.app)
#class QPushButtonRebostApp

class portrait(confStack):
	def __init_stack__(self):
		self.dbg=False
		self._debug("portrait load")
		self.menu_description=i18n.get('MENUDESCRIPTION')
		self.description=i18n.get('DESCRIPTION')
		self.icon=('application-x-desktop')
		self.tooltip=i18n.get('TOOLTIP')
		self.index=1
		self.appsToLoad=50
		self.appsLoaded=0
		self.enabled=True
		self.defaultRepos={}
		self.rc=store.client()
		self.hideControlButtons()
		self.changed=[]
		self.level='user'
		self.config={}
	#def __init__

	def _load_screen(self):
		self.config=self.getConfig()
		self.box=QGridLayout()
		self.apps=json.loads(self.rc.execute('list'))
		self._shuffleApps()
		self.setLayout(self.box)
		self.cmbCategories=QComboBox()
		self.cmbCategories.activated.connect(self._loadCategory)
		catList=json.loads(self.rc.execute('getCategories'))
		self.cmbCategories.addItem(i18n.get('ALL'))
		seenCats={}
		for cat in catList:
			if cat.lower() in seenCats.keys():
				continue
			seenCats[cat.lower()]=cat
			self.cmbCategories.addItem(cat)#.capitalize())
		self.box.addWidget(self.cmbCategories,0,0,1,1,Qt.Alignment(0))
		self.searchBox=appconfigControls.QSearchBox()
		self.box.addWidget(self.searchBox,0,1,1,1,Qt.AlignRight)
		self.searchBox.editingFinished.connect(self._searchApps)
		self.searchBox.clicked.connect(self._searchApps)
		self.table=appconfigControls.QTableTouchWidget()
		self.table.setAttribute(Qt.WA_AcceptTouchEvents)
		self.table.setColumnCount(3)
		self.table.setShowGrid(False)
		self.table.verticalHeader().hide()
		self.table.horizontalHeader().hide()
		self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
		self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
		self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
		self.table.verticalScrollBar().valueChanged.connect(self._getMoreData)
		self.resetScreen()
		self.box.addWidget(self.table,1,0,1,2)
		btnSettings=QPushButton()
		icn=QtGui.QIcon.fromTheme("settings-configure")
		btnSettings.setIcon(icn)
		btnSettings.clicked.connect(self._gotoSettings)
		self.box.addWidget(btnSettings,2,1,1,1,Qt.AlignRight)
	#def _load_screen

	def _shuffleApps(self):
		random.shuffle(self.apps)

	def _searchApps(self):
		txt=self.searchBox.text()
		self.resetScreen()
		if len(txt)==0:
			self.apps=json.loads(self.rc.execute('list'))
			self.updateScreen()
		else:
			self.apps=json.loads(self.rc.execute('search',txt))
			self.updateScreen()
	#def _searchApps

	def _gotoSettings(self):
		self.stack.gotoStack(idx=2,parms="")
	#def _gotoSettings

	def _loadCategory(self):
		self.searchBox.setText("")
		self.resetScreen()
		cat=self.cmbCategories.currentText()
		if cat==i18n.get("ALL"):
			cat=""
		self.apps=json.loads(self.rc.execute('list',cat))
		self.updateScreen()
	#def _loadCategory

	def _getMoreData(self):
		if self.table.verticalScrollBar().value()==self.table.verticalScrollBar().maximum():
			self._loadData(self.appsLoaded,self.appsLoaded+self.appsToLoad)
	#def _getMoreData

	def _loadData(self,idx,idx2,applist=None):
		if applist==None:
			apps=self.apps[idx:idx2]
		else:
			apps=applist
		col=0
		cont=self.appsToLoad
		rowspan=random.randint(1,3)
		span=rowspan
		for strapp in apps:
			row=self.table.rowCount()-1
			btn=QPushButtonRebostApp(strapp)
			btn.clicked.connect(self._loadDetails)
			self.table.setCellWidget(row,col,btn)
			self.table.setRowHeight(row,136)
			col+=1
			span=span-1
			if span==0:
				if rowspan==3:
					rowspan=1
				elif rowspan==1:
					rowspan=3
				if rowspan!=1:
					self.table.setSpan(row,col-1,1,rowspan)
				rowspan=random.randint(1,3)
				span=rowspan
				self.table.setRowCount(self.table.rowCount()+1)
				col=0
			#self.table.setCellWidget(row+1,1,desc)
			self.appsLoaded+=1
		if cont==0:
			return
		cont-=1
	#def _loadData

	def _loadDetails(self,*args):
		self.stack.gotoStack(idx=3,parms=args)
	#def _loadDetails

	def updateScreen(self):
		self._loadData(self.appsLoaded,self.appsToLoad)
		self.table.show()
	#def _udpate_screen

	def resetScreen(self):
		self.table.setRowCount(0)
		self.table.setRowCount(1)
		self.appsLoaded=0

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

