#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QPushButton,QGridLayout,QHeaderView,QHBoxLayout,QComboBox,QLineEdit,QWidget,QMenu
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal,QThread
from QtExtraWidgets import QSearchBox,QCheckableComboBox,QTableTouchWidget,QScreenShotContainer,QStackedWindowItem,QInfoLabel
from rebost import store 
from appconfig import appConfig
import subprocess
import json
import random
import gettext
_ = gettext.gettext
QString=type("")

i18n={
	"ALL":_("All"),
	"AVAILABLE":_("Available"),
	"CONFIG":_("Portrait"),
	"DESC":_("Navigate through all applications"),
	"FILTERS":_("Filters"),
	"INSTALLED":_("Installed"),
	"LLXUP":_("Launch LliurexUp"),
	"MENU":_("Show applications"),
	"SEARCH":_("Search"),
	"TOOLTIP":_("Portrait"),
	"UPGRADABLE":_("Upgradables"),
	"UPGRADES":_("There're upgrades available")
	}

class waitCursor(QThread):
	def __init__(self,parent):
		QThread.__init__(self, parent)
		self.parent=parent
	
	def run(self):
		self.parent.setCursor(Qt.WaitCursor)
#class waitCursor

class QPushButtonRebostApp(QPushButton):
	clicked=Signal("PyObject","PyObject")
	def __init__(self,strapp,parent=None):
		QPushButton.__init__(self, parent)
		self.cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		if os.path.exists(self.cacheDir)==False:
			os.makedirs(self.cacheDir)
		self.app=json.loads(strapp)
		self.setAttribute(Qt.WA_AcceptTouchEvents)
		self.setToolTip("<p>{0}</p>".format(self.app.get('summary',self.app.get('name'))))
		text="<strong>{0}</strong> - {1}".format(self.app.get('name',''),self.app.get('summary'),'')
		self.label=QLabel(text)
		self.label.setWordWrap(True)
		img=self.app.get('icon','')
		self.icon=QLabel()
		self.loadImg(self.app)
		self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
		lay=QHBoxLayout()
		lay.addStretch()
		lay.addWidget(self.icon,0)
		lay.addWidget(self.label,1)
		self.referrer=None
		self.setDefault(True)
		self.setLayout(lay)
	#def __init__

	def loadImg(self,app):
		img=app.get('icon','')
		aux=QScreenShotContainer()
		self.scr=aux.loadScreenShot(img,self.cacheDir)
		icn=''
		if os.path.isfile(img):
			icn=QtGui.QPixmap.fromImage(img)
		elif img=='':
			icn2=QtGui.QIcon.fromTheme(app.get('pkgname'))
			icn=icn2.pixmap(128,128)
		elif "flathub" in img:
			tmp=img.split("/")
			if "icons" in tmp:
				idx=tmp.index("icons")
				prefix=tmp[:idx-1]
				iconPath=os.path.join("/".join(prefix),"active","/".join(tmp[idx:]))
				if os.path.isfile(iconPath):
					icn=QtGui.QPixmap.fromImage(iconPath)

		if icn:
			wsize=128
			if "/usr/share/banners/lliurex-neu" in img:
				wsize=235
			self.icon.setPixmap(icn.scaled(wsize,128,Qt.KeepAspectRatio,Qt.SmoothTransformation))
		elif img.startswith('http'):
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
		if "0" not in str(self.app.get('state',1)):
			#self.setStyleSheet("""QPushButton{background-color: rgba(140, 255, 0, 70);}""")
			self._applyDecoration()
		if "FORBIDDEN" in self.app.get("categories",[]):
			self._applyDecoration(forbidden=True)
	#def loadImg

	def _applyDecoration(self,forbidden=False):
		self.setObjectName("rebostapp")
		self.setAttribute(Qt.WA_StyledBackground, True)
		if forbidden==False:
			bcolor=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Active,QtGui.QPalette.Mid))
			color=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Active,QtGui.QPalette.Base))
		else:
			bcolor=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Inactive,QtGui.QPalette.Light))
			color=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Inactive,QtGui.QPalette.Dark))
		self.setAutoFillBackground(True)
		pal=self.palette()
		#pal.setColor(QPalette.Window,bcolor)
		rgbColor="{0},{1},{2}".format(color.red(),color.green(),color.blue())
		rgbBcolor="{0},{1},{2}".format(bcolor.red(),bcolor.green(),bcolor.blue())
		self.setStyleSheet("""#rebostapp {
			background-color: rgb(%s); 
			border-style: solid; 
			border-color: rgb(%s); 
			border-width: 1px; 
			border-radius: 2px;}"""%(rgbColor,rgbBcolor))

	def _removeDecoration(self):
		self.setObjectName("")
		self.setStyleSheet("")

	
	def load(self,*args):
		img=args[0]
		self.icon.setPixmap(img.scaled(128,128))
	#def load
	
	def activate(self):
		self.clicked.emit(self.app)
	#def activate

	def keyPressEvent(self,ev):
		if ev.key() in [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]:
			self.clicked.emit(self,self.app)
		ev.ignore()
	#def keyPressEvent(self,ev):

	def mousePressEvent(self,*args):
		self.clicked.emit(self,self.app)
	#def mousePressEvent
#class QPushButtonRebostApp

class portrait(QStackedWindowItem):
	def __init_stack__(self):
		self.dbg=False
		self.enabled=True
		self._debug("portrait load")
		self.setProps(shortDesc=i18n.get("DESC"),
			longDesc=i18n.get("MENU"),
			icon="application-x-desktop",
			tooltip=i18n.get("TOOLTIP"),
			index=1,
			visible=True)
		self.appconfig=appConfig.appConfig()
		self.appconfig.setConfig(confDirs={'system':'/usr/share/rebost','user':os.path.join(os.environ['HOME'],'.config/rebost')},confFile="store.json")
		self.i18nCat={}
		self.catI18n={}
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
		self.level='system'
		self.oldcursor=self.cursor()
	#def __init__

	def __initScreen__(self):
		self.config=self.appconfig.getConfig()
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
		self.btnFilters=QCheckableComboBox()
		#self.btnFilters.clicked.connect(self._filterView)
		self.btnFilters.activated.connect(self._selectFilters)
		self._loadFilters()
		icn=QtGui.QIcon.fromTheme("view-filter")
		hbox.addWidget(self.btnFilters)
		wdg.setLayout(hbox)
		self.box.addWidget(wdg,0,0,1,1,Qt.AlignLeft)
		self.searchBox=QSearchBox()
		self.searchBox.setToolTip(i18n["SEARCH"])
		self.searchBox.setPlaceholderText(i18n["SEARCH"])
		self.box.addWidget(self.searchBox,0,1,1,1,Qt.AlignRight)
		self.searchBox.returnPressed.connect(self._searchApps)
		self.searchBox.textChanged.connect(self._resetSearchBtnIcon)
		self.searchBox.clicked.connect(self._searchAppsBtn)
		self.table=QTableTouchWidget()
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
		self.box.addWidget(btnSettings,2,1,1,1,Qt.Alignment(-1))
		self.lblInfo=QInfoLabel()
		self.lblInfo.setActionText(i18n.get("LLXUP"))
		self.lblInfo.setActionIcon("lliurex-up")
		self.lblInfo.setText(i18n.get("UPGRADES"))
		self.lblInfo.clicked.connect(self._launchLlxUp)
		self.box.addWidget(self.lblInfo,2,0,1,1)
		self._getUpgradables()
	#def _load_screen

	def _launchLlxUp(self):
		subprocess.run(["pkexec","lliurex-up"])

	def _loadFilters(self):
		self.btnFilters.clear()
		self.btnFilters.setText(i18n.get("FILTERS"))
		self.btnFilters.addItem(i18n.get("ALL"))
		items=[i18n.get("INSTALLED"),"Lliurex","Snap","Appimage","Flatpak","Zomando"]
		for item in items:
			self.btnFilters.addItem(item,state=False)
	#def _loadFilters

	def _populateCategories(self): 
		self.cmbCategories.clear()
		self.i18nCat={}
		self.catI18n={}
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
			self.catI18n[cat]=_(cat)
		translatedCategories.sort()

		for cat in translatedCategories:
			self.cmbCategories.addItem(cat)
	#def _populateCategories

	def _getAppList(self,cat=[]):
		apps=[]
		if isinstance(cat,str):
			cat=cat.split()
		if len(cat)>0:
			categories=",".join(cat)
			if len(cat)>1:
				apps.extend(json.loads(self.rc.execute('list',"({})".format(categories))))
			else:
				apps.extend(json.loads(self.rc.execute('list',"{}".format(categories))))
			self._debug("Loading cat {}".format(",".join(cat)))
		else:
			categories=[]
			for i18ncat,cat in self.i18nCat.items():
				categories.append("\"{}\"".format(cat))
			categories=",".join(categories)
			apps.extend(json.loads(self.rc.execute('list',"({})".format(categories))))
		self.appsRaw=apps
		return(apps)
	#def _getAppList

	def _getUpgradables(self):
		self.lblInfo.setVisible(False)
		apps=json.loads(self.rc.getUpgradableApps())
		if len(apps)>0:
			self.lblInfo.setVisible(True)
	#def _getUpgradables

	def _shuffleApps(self):
		random.shuffle(self.apps)
	#def _shuffleApps

	def _goHome(self):
		self.searchBox.setText("")
		self._loadFilters()
		self.apps=self._getAppList()
		self._shuffleApps()
		self.resetScreen()
		self.cmbCategories.setCurrentIndex(0)
		self.updateScreen()
	#def _goHome

	def _filterView(self,getApps=True):
		filters={}
		appsFiltered=[]
		self.apps=self.appsRaw
		self.resetScreen()
		filters=self._readFilters()
		if len(filters)==0:
			filters['package']=True
		if filters.get("lliurex",False)==True:
			self.apps=self._getAppList(["\"Lliurex\"","\"Lliurex-Administration\"","\"Lliurex-Infantil\""])
		self.apps=self._applyFilters(filters)
		self.updateScreen()
	#def _filterView

	def _readFilters(self):
		filters={}
		for item in self.btnFilters.getItems():
			if item.checkState()==Qt.Checked:
				filters[item.text().lower()]=True
		if len(filters)>1:
			filters[i18n.get("ALL").lower()]=False
		return(filters)
	#def _readFilters

	def _applyFilters(self,filters):
		appsFiltered=[]
		filterList=False
		if filters.get(i18n.get("ALL").lower(),False)!=True:
			for app in self.apps:
				japp=json.loads(app)
				#Filter bundles
				flterList=False
				for bund in ["appimage","flatpak","snap","zomando"]:
					if bund  in filters.keys():
						filterList=True
						break
				for bund in japp.get('bundle',{}).keys():
					if filters.get(i18n.get("UPGRADABLE",False))==True:
						state=japp.get('state',{})
						installed=japp.get('installed',{}).get(bund,"")
						if state.get(bund,"1")=="0":
							available=japp.get('versions',{}).get(bund,"")
							if available=="" or available==installed:
								continue
						else:
							continue
					if filters.get(i18n.get("INSTALLED").lower(),False)==True:
						state=japp.get('state',{})
						if state.get(bund,"1")!="0":
							continue
					if bund not in filters.keys() and filterList==True:
						continue
					if app not in appsFiltered:
						appsFiltered.append(app)
		else:
			appsFiltered=self.appsRaw
		return(appsFiltered)
	#def _applyFilters

	def _selectFilters(self,*args):
		cat=""
		if len(args)>0:
			idx=args[0]
		else:
			idx=self.btnFilters.currentIndex()
		if idx<1:
			return
		item=self.btnFilters.model().item(idx)
		state=item.checkState()
		if state==Qt.Checked:
			state=Qt.Unchecked
			init=2
		else:
			state=Qt.Checked
			init=4
		if idx==1:
			for i in (range(init,self.btnFilters.count())):
				item=self.btnFilters.model().item(i)
				item.setCheckState(state)
		elif state==Qt.Unchecked: # -> Remember: swap
			item=self.btnFilters.model().item(1)
			item.setCheckState(Qt.Unchecked)
		self._filterView(getApps=False)
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
		self.oldSearch=txt
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

	def _loadDetails(self,*args,**kwargs):
		c=waitCursor(self)
		c.finished.connect(lambda:self._endLoadDetails(*args))
		c.start()
	#def _loadDetails(self,*args,**kwargs):

	def _endLoadDetails(self,*args):
#		self.stack.gotoStack(idx=3,parms=(args))
		#Refresh all pkg info
		self.referrer=args[0]
		self.setChanged(False)
		self.parent.setCurrentStack(idx=3,parms=args[-1].get("name",""))
	#def _loadDetails

	def _gotoSettings(self):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		self.parent.setCurrentStack(idx=2,parms="")
	#def _gotoSettings

	def updateScreen(self):
		self._loadData(self.appsLoaded,self.appsToLoad)
		#self.table.show()
		self.setCursor(self.oldcursor)
	#def _udpate_screen

	def resetScreen(self):
		self.table.setRowCount(0)
		self.table.setRowCount(1)
		self.appsLoaded=0
		self.oldSearch=""
		self.appsSeen=[]
	#def resetScreen

	def setParms(self,*args,**kwargs):
		for arg in args:
			if isinstance(arg,dict):
				for key,item in arg.items():
					kwargs[key]=item
		if kwargs.get("refresh",False)==False:
			cursor=QtGui.QCursor(Qt.WaitCursor)
			self.setCursor(cursor)
			if len(args)>=1:
				self._populateCategories()
				self.oldSearch=""
				self._searchApps()
		else:
			if hasattr(self,"referrer")==False:
				return()
			app=kwargs.get("app",{})
			cat=kwargs.get("cat",{})
			if len(cat)>0:
				self.cmbCategories.setCurrentText(self.catI18n.get(cat,cat))
				self._loadCategory()
			else:
				if "FORBIDDEN" in app.get("categories",[]):
					self.referrer._applyDecoration(forbidden=True)
				elif "0" not in str(app.get('state',1)):
					#self.setStyleSheet("""QPushButton{background-color: rgba(140, 255, 0, 70);}""")
					self.referrer._applyDecoration()
				elif self.referrer!=None:
					self.referrer._removeDecoration()
	#def setParms

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

