#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QPushButton,QGridLayout,QSizePolicy,QWidget,QComboBox,QDialog,QDialogButtonBox,QVBoxLayout,QTableWidget,QHeaderView,QHBoxLayout
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal,QThread
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appconfigControls
from rebost import store
import subprocess
from multiprocessing import Process
import json
import random
import html
import gettext
import requests
_ = gettext.gettext
QString=type("")

i18n={
	"CONFIG":_("Details"),
	"DESCRIPTION":_("Show application detail"),
	"MENUDESCRIPTION":_("Navigate through all applications"),
	"TOOLTIP":_(""),
	"INSTALL":_("Install"),
	"RUN":_("Open"),
	"REMOVE":_("Remove"),
	"UPGRADE":_("Upgrade"),
	"ZMDNOTFOUND":_("Zommand not found. Open Zero-Center?")
	}
	
class epiClass(QThread):
	epiEnded=Signal("PyObject")
	def __init__(self,parent=None):
		QThread.__init__(self, parent)
		self.app={}
		self.args=''
	#def __init__

	def setArgs(self,app,args,bundle=""):
		self.app=app
		self.args=args
		if bundle:
			oldBundle=self.app.get('bundle')
			newBundle={bundle:oldBundle.get(bundle)}
			self.app['bundle']=newBundle

	#def setArgs

	def run(self):
		launched=False
		if self.app and self.args:
			subprocess.run(self.args)
			self.epiEnded.emit(self.app)
			launched=True
		return launched
	#def run
#class epiClass


class QLabelRebostApp(QLabel):
	clicked=Signal("PyObject")
	def __init__(self,parent=None):
		QLabel.__init__(self, parent)
		self.cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
	#def __init__

	def loadImg(self,app):
		img=app.get('icon','')
		self.scr=appconfigControls.loadScreenShot(img,self.cacheDir)
		icn=''
		if os.path.isfile(img):
			icn=QtGui.QPixmap.fromImage(img)
		elif img=='':
			icn2=QtGui.QIcon.fromTheme('application-x-executable')
			icn=icn2.pixmap(128,128)
		if icn:
			wsize=128
			if "Zomando" in app.get("categories") or "zero" in app.get('pkgname').lower():
				wsize=235
			self.setPixmap(icn.scaled(wsize,128))
		elif img.startswith('http'):
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
	#def loadImg
	
	def load(self,*args):
		img=args[0]
		self.setPixmap(img.scaled(128,128))
	#def load
#class QLabelRebostApp

class details(confStack):
	def __init_stack__(self):
		self.dbg=True
		self._debug("details load")
		self.menu_description=i18n.get('MENUDESCRIPTION')
		self.description=i18n.get('DESCRIPTION')
		self.icon=('application-x-desktop')
		self.tooltip=i18n.get('TOOLTIP')
		self.index=3
		self.visible=False
		self.enabled=True
		self.rc=store.client()
		self.changed=[]
		self.level='user'
		self.config={}
		self.app={}
		self.hideControlButtons()
		self.cacheDir=os.path.join(os.environ.get('HOME'),".cache","rebost","imgs")
		self.epi=epiClass()
	#def __init__

	def _return(self):
		self.stack.gotoStack(idx=1,parms="")
	#def _return

	def _load_screen(self):
		self.box=QGridLayout()
		self.btnBack=QPushButton()
		icn=QtGui.QIcon.fromTheme("go-previous")
		self.btnBack.setIcon(icn)
		self.btnBack.clicked.connect(self._return)
		self.btnBack.setIconSize(QSize(48,48))
		self.btnBack.setFixedSize(QSize(64,64))
		self.box.addWidget(self.btnBack,0,0,1,1)
		self.lblIcon=QLabelRebostApp()         
		self.box.addWidget(self.lblIcon,0,1,2,1,Qt.AlignTop|Qt.AlignLeft)
		self.lblName=QLabel()
		self.box.addWidget(self.lblName,0,2,1,1,Qt.AlignTop)
		self.lblSummary=QLabel()
		self.lblSummary.setWordWrap(True)
		self.box.addWidget(self.lblSummary,1,2,1,1,Qt.AlignTop)
		self.launchers=QWidget()
		lay=QHBoxLayout()
		self.cmbInstall=QComboBox()
		self.cmbInstall.activated.connect(self._genericEpiInstall)
		#self.box.addWidget(self.cmbInstall,3,0,1,1,Qt.AlignTop)
		lay.addWidget(self.cmbInstall,Qt.AlignLeft)
		self.cmbRemove=QComboBox()
		self.cmbRemove.activated.connect(self._genericEpiInstall)
		lay.addWidget(self.cmbRemove,Qt.AlignLeft)
		#self.box.addWidget(self.cmbRemove,4,0,1,1,Qt.AlignTop)
		self.cmbOpen=QComboBox()
		self.cmbOpen.activated.connect(self._runApp)
		self.btnZomando=QPushButton("{} zomando".format(i18n.get("RUN")))
		self.btnZomando.clicked.connect(self._runZomando)
		self.btnZomando.setVisible(False)
		#self.box.addWidget(self.btnZomando,4,0,1,1)
		lay.addWidget(self.btnZomando,Qt.AlignLeft)
		#self.box.addWidget(self.cmbOpen,5,0,1,1)
		lay.addWidget(self.cmbOpen,Qt.AlignLeft)
		self.launchers.setLayout(lay)
		self.box.addWidget(self.launchers,2,0,1,2,Qt.AlignTop|Qt.AlignLeft)
#		self.tableBox=QTableWidget(1,1)
#
#		self.tableBox.verticalHeader().hide()
#		self.tableBox.horizontalHeader().hide()
#		#self.tableBox.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
#		self.tableBox.verticalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
#		self.box.addWidget(self.tableBox,2,1,1,1)
		self.lblDesc=appconfigControls.QScrollLabel()
		self.lblDesc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.lblDesc.setWordWrap(True)	  
#		self.tableBox.setCellWidget(0,0,self.lblDesc)
		self.screenShot=appconfigControls.QScreenShotContainer()
		#self.tableBox.setCellWidget(1,0,self.screenShot)
		self.box.addWidget(self.lblDesc,3,0,1,3)
		#self.box.addWidget(launchers,3,0,1,1)
		self.lblHomepage=QLabel('<a href="http://lliurex.net">Homepage: lliurex.net</a>')
		self.lblHomepage.setOpenExternalLinks(True)
		self.box.addWidget(self.lblHomepage,4,0,1,3)
		#self.tableBox.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
		self.box.addWidget(self.screenShot,5,0,1,3,Qt.AlignTop)
		self.box.setColumnStretch(0,0)
		self.box.setColumnStretch(1,0)
		self.box.setColumnStretch(2,2)
		self.box.setRowStretch(0,0)
		self.box.setRowStretch(1,0)
		self.box.setRowStretch(2,0)
		self.box.setRowStretch(3,2)
		self.box.setRowStretch(4,1)
		self.setLayout(self.box)
	#def _load_screen

	def resizeEvent(self,*args):
		print(self.sizeHint())
		#self.lblDesc.setMaximumWidth(self.sizeHint().width()-124)#,self.height()/2)
		#self.lblDesc.setMaximumHeight(self.tableBox.sizeHint().height())#,self.height()/2)
		#self.lblDesc.setMaximumHeight(self.screenShot.sizeHint().height())#,self.height()/2)
		#self.lblDesc.setWidth(self.screenShot.width())#,self.height()/2)
		#self.screenShot.setFixedWidth(self.lblDesc.width())#,self.height()/2)
		pass

	def _runZomando(self):
		zmdPath=os.path.join("/usr/share/zero-center/zmds",self.app.get('bundle',{}).get('zomando',''))
		if zmdPath.endswith(".zmd")==False:
			zmdPath="{}.zmd".format(zmdPath)
		if os.path.isfile(zmdPath):
			#Look if pkexec is needed
			appPath=os.path.join("/usr/share/zero-center/applications",self.app.get('bundle',{}).get('zomando','')).replace(".zmd",".app")
			if appPath.endswith(".app")==False:
				appPath="{}.app".format(appPath)
			cmd=[zmdPath]
			if os.path.isfile(appPath):
				with open (appPath,'r') as f:
					flines=f.readlines()
				for l in flines:
					if "pkexec" in l:
						cmd=["pkexec",zmdPath]
						break
			#subprocess.run(["pkexec",zmdPath])
			try:
				subprocess.run(cmd)
			except Exception as e:
				print(e)
				self.showMsg(e)
		else:
			self._zmdNotFound(zmdPath)
	#def _runZomando

	def _zmdNotFound(self,zmd):
		def _launchZeroCenter():
			dlg.close()
			cmd=["zero-center"]
			try:
				subprocess.run(cmd)
			except Exception as e:
				print(e)
				self.showMsg(e)

		dlg=QDialog()
		dlg.setWindowTitle("Error")
		btns=QDialogButtonBox.Open|QDialogButtonBox.Cancel
		dlgBtn=QDialogButtonBox(btns)
		dlgBtn.accepted.connect(_launchZeroCenter)
		dlgBtn.rejected.connect(dlg.close)
		lay=QGridLayout()
		lbl=QLabel("{0}".format(i18n.get("ZMDNOTFOUND")))
		lay.addWidget(lbl)
		lay.addWidget(dlgBtn)
		dlg.setLayout(lay)
		dlg.exec()

	def _runApp(self):
		bundle=self.cmbOpen.currentText().lower().split(" ")[0]
		if bundle=="package":
			cmd=["gtk-launch",self.app.get("name",'')]
		elif bundle=="flatpak":
			cmd=["flatpak","run",self.app.get("bundle",{}).get("flatpak","")]
		elif bundle=="snap":
			cmd=["snap","run",self.app.get("bundle",{}).get("snap","")]
		elif bundle=="appimage":
			cmd=["gtk-launch","{}-appimage".format(self.app.get("name",''))]
		subprocess.run(cmd)
		self.cmbOpen.setCurrentIndex(-1)
	#def _runApp

	def _genericEpiInstall(self):
		bundle=self.cmbInstall.currentText().lower().split(" ")[0]
		if bundle=="":
			bundle=self.cmbRemove.currentText().lower().split(" ")[0]
		self.rc.enableGui(True)
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		pkg=self.app.get('name').replace(' ','')
		user=os.environ.get('USER')
		res=self.rc.testInstall("{}".format(pkg),"{}".format(bundle),user=user)
		res=json.loads(res)[0]
		epi=res.get('epi')
		if epi==None:
			self.showMsg("{}".format(res.get('msg','Unknown Error')))
		else:
			cmd=["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')]
			self.epi.setArgs(self.app,cmd,bundle)
			self.epi.epiEnded.connect(self._getEpiResults)
			self.epi.start()
		self.cmbInstall.setCurrentIndex(-1)
		self.cmbRemove.setCurrentIndex(-1)
	#def _genericEpiInstall
	
	def _getEpiResults(self,app):
		if app.get('name','')!=self.app.get('name',''):
			return
		self.app=json.loads(self.rc.showApp(app.get('name','')))[0]
		bundle=list(app.get('bundle').keys())[0]
		state=app.get('state',{}).get(bundle,1)
		self.rc.commitInstall(app.get('name'),bundle,state)
		if isinstance(self.app,str):
			try:
				self.app=json.loads(self.app)
			except Exception as e:
				print(e)
				self.app={}
		self.updateScreen()
	#def _getEpiResults

	def setParms(self,*args):
		swErr=False
		try:
			self.app=json.loads(args[0])
		except:
			swErr=True
		if swErr==False:
			if isinstance(self.app[0],str):
				try:
					self.app=json.loads(self.app[0])
				except Exception as e:
					swErr=True
					print(e)
		if swErr:
			self.app={}
		for bundle,name in (self.app.get('bundle',{}).items()):
			if bundle=='package':
				continue
			name=self.app.get('name','')
			if name!='':
				status=self.rc.getAppStatus(name,bundle)
				self.app['state'][bundle]=str(status)
		#self.lblDesc.setMaximumWidth(self.height())#,self.height()/2)
		#self.lblDesc.setMaximumHeight(10)#,self.height()/2)
		cursor=QtGui.QCursor(Qt.PointingHandCursor)
		self.setCursor(cursor)
	#def setParms

	def updateScreen(self):
		self._initScreen()
		self.lblName.setText("<h1>{}</h1>".format(self.app.get('name')))
		icn=QtGui.QPixmap.fromImage(self.app.get('icon',''))
		if icn.depth()==0:
		#something went wrong. Perhaps img it's gzipped
			icn2=QtGui.QIcon.fromTheme('application-x-executable')
			icn=icn2.pixmap(128,128)
		self.lblIcon.setPixmap(icn.scaled(128,128))
		self.lblIcon.loadImg(self.app)
		self.lblSummary.setText("<h2>{}</h2>".format(self.app.get('summary','')))
		self.lblDesc.setText(html.unescape(self.app.get('description','')))
		versions=self.app.get('versions',{})
		self.cmbRemove.setVisible(False)
		self.cmbOpen.setVisible(False)
		self.cmbInstall.setVisible(False)
		bundles=list(self.app.get('bundle',{}).keys())
		pkgState=0
		if "zomando" in bundles:
			if "package" in bundles:
				pkgState=self.app.get('state',{}).get("package",'1')
				if pkgState=="0":
					bundles.remove('package')
		for bundle in bundles:
			state=self.app.get('state',{}).get(bundle,'1')
			if bundle=="zomando" and (pkgState=="0" or state=="0"):
				self.btnZomando.setVisible(True)
				continue
			elif bundle=="zomando":
				continue
		#		self.btnPackageLaunch.setVisible(False)
			tooltip=self.app.get('versions',{}).get(bundle,'')
			tipInfo=tooltip
			if len(tooltip)>8:
				tipArray=tooltip.split(".")
				count=0
				while len(tipInfo)<8 or count>=len(tipArray):
					tipInfo=".".join(tipArray[0:count])
					count+=1
				if len(tipInfo)>8:
					tipInfo=tipInfo[0:8]
			if state=='0':
				self.cmbRemove.setVisible(True)
				self.cmbRemove.addItem("{0} {1}".format(bundle.capitalize(),tipInfo))
				self.cmbRemove.setItemData(self.cmbRemove.count()-1,tooltip,Qt.ToolTipRole)
				self.cmbOpen.setVisible(True)
				self.cmbOpen.addItem("{0} {1}".format(bundle.capitalize(),tipInfo))
				self.cmbOpen.setItemData(self.cmbOpen.count()-1,tooltip,Qt.ToolTipRole)
			else:
				self.cmbInstall.setVisible(True)
				self.cmbInstall.addItem("{0} {1}".format(bundle.capitalize(),tipInfo))
				self.cmbInstall.setItemData(self.cmbInstall.count()-1,tooltip,Qt.ToolTipRole)

		homepage=self.app.get('homepage','')
		text=''
		if homepage:
			if homepage.endswith("/"):
				homepage=homepage.rstrip("/")
			desc=homepage
			if len(homepage)>30:
				desc="{}...".format(homepage[0:30])
			text='<a href={0}>Homepage: {1}</a> '.format(homepage,desc)
		license=self.app.get('license','')
		if license:
			text+="<strong>{}</strong>".format(license)
		self.lblHomepage.setText(text)
		self.lblHomepage.setToolTip("{}".format(homepage))
		try:
			for icn in self.app.get('screenshots',[]):
				self.screenShot.addImage(icn)
		except Exception as e:
			print(e)
	#def _udpate_screen

	def _initScreen(self):
		#Reload config if app has been epified
		if len(self.app)>0:
			if self.app.get('name','')==self.epi.app.get('name',''):
				try:
					self.app=json.loads(self.rc.showApp(self.app.get('name','')))[0]
				except Exception as e:
					print(e)
			if isinstance(self.app,str):
				try:
					self.app=json.loads(self.app)
				except Exception as e:
					print(e)
					self.app={}
		cursor=QtGui.QCursor(Qt.PointingHandCursor)
		self.setCursor(cursor)
		self.screenShot.clear()
		self.btnZomando.setVisible(False)
		self.cmbInstall.clear()
		self.cmbInstall.setPlaceholderText("{}...".format(i18n.get("INSTALL")))
		self.cmbRemove.clear()
		self.cmbRemove.setPlaceholderText("{}...".format(i18n.get("REMOVE")))
		self.cmbOpen.clear()
		self.cmbOpen.setPlaceholderText("{}...".format(i18n.get("RUN")))
		#self.lblSummary.setFixedWidth(self.height())
		self.lblHomepage.setText("")
		self.app['name']=self.app.get('name','').replace(" ","")
	#def _initScreen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

