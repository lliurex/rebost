#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QPushButton,QGridLayout,QHeaderView,QHBoxLayout,QComboBox,QLineEdit,QWidget,QMenu
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal
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
	"SEARCH":_("Search"),
	"ALL":_("All"),
	"FILTERS":_("Filters"),
	"AVAILABLE":_("Available"),
	"INSTALLED":_("Installed"),
	"UPGRADABLE":_("Upgradables")
	}

class QPushButtonRebostApp(QPushButton):
	clicked=Signal("PyObject")
	def __init__(self,strapp,parent=None):
		QPushButton.__init__(self, parent)
		self.cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		self.app=json.loads(strapp)
		self.setAttribute(Qt.WA_AcceptTouchEvents)
		text="<strong>{0}</strong> - {1}".format(self.app.get('name',''),self.app.get('summary'),'')
		self.label=QLabel(text)
		self.label.setWordWrap(True)
		img=self.app.get('icon','')
		self.icon=QLabel()
		icn=''
		if os.path.isfile(img):
			icn=QtGui.QPixmap.fromImage(img)
		elif img=='':
			icn2=QtGui.QIcon.fromTheme('application-x-executable')
			icn=icn2.pixmap(128,128)
		if icn:
			self.load(icn)
		elif img.startswith('http'):
			self.scr=appconfigControls.loadScreenShot(img,self.cacheDir)
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
		lay=QHBoxLayout()
		lay.addStretch()
		lay.addWidget(self.icon,0)
		lay.addWidget(self.label,1)
		self.setLayout(lay)
	#def __init__
	
	def load(self,*args):
		img=args[0]
		if "0" in str(self.app.get('state',1)):
			self.setStyleSheet("""QPushButton{background-color: rgba(140, 255, 0, 70);}""")
		self.icon.setPixmap(img.scaled(128,128))
	#def load
	
	def activate(self):
		self.clicked.emit(self.app)
	#def activate

	def mousePressEvent(self,*args):
		self.clicked.emit(self.app)
	#def mousePressEvent
#class QPushButtonRebostApp

class portrait(confStack):
	def __init_stack__(self):
		self.dbg=False
		self.enabled=True
		self._debug("portrait load")
		self.menu_description=i18n.get('MENUDESCRIPTION')
		self.description=i18n.get('DESCRIPTION')
		self.icon=('application-x-desktop')
		self.tooltip=i18n.get('TOOLTIP')
		self.i18nCat={}
		self.config={}
		self.index=1
		self.appsToLoad=50
		self.appsLoaded=0
		self.appsSeen=[]
		self.appsRaw=[]
		self.oldSearch=""
		self.defaultRepos={}
		self.rc=store.client()
		self.hideControlButtons()
		self.changed=[]
		self.level='user'
	#def __init__

	def _load_screen(self):
		self.config=self.getConfig()
		self.box=QGridLayout()
		self.setLayout(self.box)
		wdg=QWidget()
		hbox=QHBoxLayout()
		btnHome=QPushButton()
		icn=QtGui.QIcon.fromTheme("home")
		btnHome.setIcon(icn)
		btnHome.clicked.connect(self._goHome)
		hbox.addWidget(btnHome)
		self.cmbCategories=QComboBox()
		self.cmbCategories.activated.connect(self._loadCategory)
		hbox.addWidget(self.cmbCategories)
		self._populateCategories()
		self.apps=self._getAppList()
		self._shuffleApps()
		self.btnFilters=appconfigControls.QCheckableComboBox()
		self.btnFilters.activated.connect(self._selectFilters)
		self.btnFilters.clicked.connect(self._filterView)
		self._loadFilters()
		icn=QtGui.QIcon.fromTheme("view-filter")
		hbox.addWidget(self.btnFilters)
		wdg.setLayout(hbox)
		self.box.addWidget(wdg,0,0,1,1,Qt.AlignLeft)
		self.searchBox=appconfigControls.QSearchBox()
		self.searchBox.setToolTip(i18n["SEARCH"])
		self.searchBox.setPlaceholderText(i18n["SEARCH"])
		self.box.addWidget(self.searchBox,0,1,1,1,Qt.AlignRight)
		self.searchBox.returnPressed.connect(self._searchApps)
		self.searchBox.textChanged.connect(self._resetSearchBtnIcon)
		self.searchBox.clicked.connect(self._searchAppsBtn)
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

	def _loadFilters(self):
		self.btnFilters.clear()
		self.btnFilters.setText(i18n.get("FILTERS"))
		self.btnFilters.addItem(i18n.get("ALL"))
		self.btnFilters.addItem(i18n.get("INSTALLED"),state=False)
		self.btnFilters.addItem("Snap",state=False)
		self.btnFilters.addItem("Appimage",state=False)
		self.btnFilters.addItem("Flatpak",state=False)
		self.btnFilters.addItem("Zomando",state=False)
	#def _loadFilters

	def _populateCategories(self): 
		self.cmbCategories.clear()
		self.i18nCat={}
		catList=json.loads(self.rc.execute('getCategories'))
		self.cmbCategories.addItem(i18n.get('ALL'))
		seenCats={}
		#Sort categories
		translatedCategories=[]
		for cat in catList:
			#if cat.islower() it's a category from system without appstream info 
			if _(cat) in self.i18nCat.keys() or cat.islower():
				continue
			translatedCategories.append(_(cat))
			self.i18nCat[_(cat)]=cat
		translatedCategories.sort()

		for cat in translatedCategories:
			self.cmbCategories.addItem(cat)
	#def _populateCategories

	def _getAppList(self,cat=''):
		apps=[]
		if cat!='':
			apps=json.loads(self.rc.execute('list',"\"{}\"".format(cat)))
			self._debug("Loading cat {}".format(cat))
		else:
			categories=[]
			for i18ncat,cat in self.i18nCat.items():
				categories.append("\"{}\"".format(cat))
			categories=",".join(categories)
			apps.extend(json.loads(self.rc.execute('list',"({})".format(categories))))
		self.appsRaw=apps
		return(apps)
	#def _getAppList

	def _shuffleApps(self):
		random.shuffle(self.apps)
	#def _shuffleApps

	def _goHome(self):
		self._loadFilters()
		self.apps=self._getAppList()
		self._shuffleApps()
		self.resetScreen()
		self.cmbCategories.setCurrentIndex(0)
		self.updateScreen()
	#def _goHome

	def _filterView(self,getApps=True):
		idx=self.btnFilters.currentIndex()
		filters={}
		appsFiltered=[]
		self.apps=self.appsRaw
		applyFilter=False
		applyFilterBundle=False
		self.resetScreen()
		for item in self.btnFilters.getItems():
			if item.text().lower()==i18n.get("ALL").lower() and idx<=1:
				continue
			filters[item.text().lower()]=item.checkState()
			if item.checkState()==Qt.Checked:
				if item.text().lower() in ["zomando","flatpak","appimage","snap"]:
					applyFilterBundle=True
				applyFilter=True
		if applyFilterBundle==False:
			for bund in ["zomando","flatpak","appimage","snap"]:
				filters[bund]=Qt.Checked
		if filters.get(i18n.get("ALL").lower(),Qt.Unchecked)!=Qt.Checked and applyFilter==True:
			for app in self.apps:
				japp=json.loads(app)
				#Filter bundles
				tmpApp=None
				for bund in japp.get('bundle',{}).keys():
					if bund in filters.keys():
						if filters[bund]==Qt.Checked:
							tmpApp=app
					if tmpApp:
						if filters.get(i18n.get("INSTALLED",'').lower())==Qt.Checked:
							state=japp.get('state',{})
							if state.get(bund,"1")!="0":
								tmpApp=None
						if filters.get(i18n.get("UPGRADABLE",'').lower())==Qt.Checked:
							state=japp.get('state',{})
							installed=japp.get('installed',{}).get(bund,"")
							if state.get(bund,"1")=="0":
								available=japp.get('versions',{}).get(bund,"")
								if available=="" or available==installed:
									tmpApp=None
							else:
								tmpApp=None
				if tmpApp:
					appsFiltered.append(app)
			self.apps=appsFiltered
		idx=self.btnFilters.currentIndex()
		self.updateScreen()
	#def _filterView

	def _selectFilters(self,*args):
		idx=self.btnFilters.currentIndex()
		if idx<1:
			return
		if idx==1:
			item=self.btnFilters.model().item(idx)
			if item.checkState()==Qt.Checked:
				state=Qt.Unchecked
				init=2
			else:
				state=Qt.Checked	
				init=3
			for i in (range(init,self.btnFilters.count())):
				item=self.btnFilters.model().item(i)
				item.setCheckState(state)
		else:
			item=self.btnFilters.model().item(1)
			item.setCheckState(Qt.Unchecked)
	#def _selectFilters

	def _resetSearchBtnIcon(self):
		txt=self.searchBox.text()
		if txt==self.oldSearch:
			icn=QtGui.QIcon.fromTheme("dialog-cancel")
		else:
			icn=QtGui.QIcon.fromTheme("search")
		self.searchBox.btnSearch.setIcon(icn)
	#def _resetSearchBtnIcon

	def _searchApps(self):
		self.cmbCategories.setCurrentText(i18n.get("ALL"))
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		txt=self.searchBox.text()
		if txt==self.oldSearch:
			self.searchBox.setText("")
			txt=""
		self.oldSearch=txt
		self.resetScreen()
		if len(txt)==0:
			icn=QtGui.QIcon.fromTheme("search")
			self.apps=self._getAppList()
		else:
			icn=QtGui.QIcon.fromTheme("dialog-cancel")
			self.apps=json.loads(self.rc.execute('search',txt))
			self.appsRaw=self.apps
		self.searchBox.btnSearch.setIcon(icn)
		self._filterView(getApps=False)
	#def _searchApps

	def _searchAppsBtn(self):
		txt=self.searchBox.text()
		if txt==self.oldSearch:
			self.searchBox.setText("")
			txt=""
		self._searchApps()
	#def _searchAppsBtn

	def _loadCategory(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		self.searchBox.setText("")
		self.resetScreen()
		i18ncat=self.cmbCategories.currentText()
		cat=self.i18nCat.get(i18ncat,i18ncat)
		if cat==i18n.get("ALL"):
			cat=""
		self.apps=self._getAppList(cat)
		self._filterView(getApps=False)
	#def _loadCategory

	def _getMoreData(self):
		if self.table.verticalScrollBar().value()==self.table.verticalScrollBar().maximum():
			self._loadData(self.appsLoaded,self.appsLoaded+self.appsToLoad)
	#def _getMoreData

	def _loadData(self,idx,idx2,applist=None):
		if applist==None:
			apps=self.apps[idx:idx2]
		else:
			apps=applist[idx:idx2]
		col=0
		cont=self.appsToLoad
		rowspan=random.randint(1,3)
		span=rowspan
		for strapp in apps:
			jsonapp=json.loads(strapp)
			if jsonapp.get('name','') in self.appsSeen:
				continue
			self.appsSeen.append(jsonapp.get('name',''))
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
			self.appsLoaded+=1
		if cont==0:
			return
		cont-=1
	#def _loadData

	def _loadDetails(self,*args):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
#		self.stack.gotoStack(idx=3,parms=(args))
		#Refresh all pkg info
		app=self.rc.showApp(args[0].get('name',''))
		self.stack.gotoStack(idx=3,parms=app)
	#def _loadDetails

	def _gotoSettings(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		self.stack.gotoStack(idx=2,parms="")
	#def _gotoSettings

	def updateScreen(self):
		self._loadData(self.appsLoaded,self.appsToLoad)
		self.table.show()
		cursor=QtGui.QCursor(Qt.PointingHandCursor)
		self.setCursor(cursor)
	#def _udpate_screen

	def resetScreen(self):
		self.table.setRowCount(0)
		self.table.setRowCount(1)
		self.appsLoaded=0
		self.appsSeen=[]
	#def resetScreen

	def setParms(self,*args):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		if len(args)>=1:
			self._populateCategories()
			self.oldSearch=""
			self._searchApps()
	#def setParms

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

