#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QPushButton,QGridLayout,QSizePolicy
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appconfigControls
from rebost import store
import subprocess
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
	"RUN":_("Execute"),
	"REMOVE":_("Remove")
	}
	

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
			self.setPixmap(icn.scaled(128,128))
		elif img.startswith('http'):
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
	
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
	#def __init__

	def _return(self):
		self.stack.gotoStack(idx=1,parms="")

	def _load_screen(self):
		self.box=QGridLayout()
		self.btnBack=QPushButton()
		icn=QtGui.QIcon.fromTheme("go-previous")
		self.btnBack.setIcon(icn)
		self.btnBack.clicked.connect(self._return)
		self.btnBack.setIconSize(QSize(48,48))
		self.btnBack.setFixedSize(QSize(64,64))
		self.box.addWidget(self.btnBack,0,0,1,1,Qt.AlignTop)
		self.lblIcon=QLabelRebostApp()
		self.box.addWidget(self.lblIcon,1,0,2,1,Qt.AlignTop)
		self.lblName=QLabel()
		self.box.addWidget(self.lblName,0,1,1,1,Qt.AlignTop)
		self.lblSummary=QLabel()
		self.lblSummary.setWordWrap(True)
		self.box.addWidget(self.lblSummary,1,1,1,1,Qt.AlignTop)
		self.lblDesc=appconfigControls.QScrollLabel()
		self.lblDesc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.lblDesc.setWordWrap(True)	  
		self.box.addWidget(self.lblDesc,2,1,6,1,Qt.AlignTop|Qt.AlignLeft)
		self.btnApt=QPushButton("{} package".format(i18n.get("INSTALL")))
		self.btnApt.clicked.connect(self._installApt)
		self.box.addWidget(self.btnApt,3,0,1,1,Qt.AlignTop)
		self.btnFlat=QPushButton("{} flatpak".format(i18n.get("INSTALL")))
		self.btnFlat.clicked.connect(self._installFlat)
		self.box.addWidget(self.btnFlat,4,0,1,1,Qt.AlignTop)
		self.btnSnap=QPushButton("{} snap".format(i18n.get("INSTALL")))
		self.btnSnap.clicked.connect(self._installSnap)
		self.box.addWidget(self.btnSnap,5,0,1,1,Qt.AlignTop)
		self.btnImage=QPushButton("{} appimage".format(i18n.get("INSTALL")))
		self.btnImage.clicked.connect(self._installImage)
		self.box.addWidget(self.btnImage,6,0,1,1,Qt.AlignTop)
		self.btnZomando=QPushButton("{} zomando".format(i18n.get("RUN")))
		self.btnZomando.clicked.connect(self._runZomando)
		self.box.addWidget(self.btnZomando,7,0,1,1,Qt.AlignTop)
		self.btnZomando.setVisible(False)
		self.lblHomepage=QLabel('<a href="http://lliurex.net">Homepage: lliurex.net</a>')
		self.lblHomepage.setOpenExternalLinks(True)
		self.box.addWidget(self.lblHomepage,6,1,1,1,Qt.AlignTop)
		self.btnApt.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnFlat.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnSnap.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnImage.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnZomando.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		#self.lblDesc.setFixedSize(self.height(),self.height()/2)
		self.Screenshot=appconfigControls.QScreenShotContainer()
#		self.Screenshot.setCacheDir(self.cacheDir)
		self.box.addWidget(self.Screenshot,8,0,1,2,Qt.AlignTop)
		self.setLayout(self.box)
	#def _load_screen

	def _installApt(self):
		self._genericEpiInstall("package")
	#def _installApt

	def _installFlat(self):
		self._genericEpiInstall("flatpak")
	#def _installFlat

	def _installSnap(self):
		self._genericEpiInstall("snap")
	#def _installSnap

	def _installImage(self):
		self._genericEpiInstall("appimage")
	#def _installImage

	def _runZomando(self):
		zmdPath=os.path.join("/usr/share/zero-center/zmds",self.app.get('bundle',{}).get('zomando',''))
		if os.path.isfile(zmdPath):
			subprocess.run(["pkexec",zmdPath])

	def _genericEpiInstall(self,bundle):
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		pkg=self.app.get('name').replace(' ','')
		res=self.rc.testInstall("{}".format(pkg),"{}".format(bundle))
		res=json.loads(res)[0]
		epi=res.get('epi')
		if epi==None:
			self.showMsg("{}".format(res.get('msg','Unknown Error')))
		else:
			subprocess.run(["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')])
			self.app=json.loads(self.rc.showApp(self.app.get('name')))[0]
			if isinstance(self.app,str):
				try:
					self.app=json.loads(self.app)
				except Exception as e:
					print(e)
					self.app={}
		self.updateScreen()
	#def _genericEpiInstall

	def setParms(self,*args):
		self.app=args[0][0]

	def updateScreen(self):
		self._initScreen()
		self.lblName.setText("<h1>{}</h1>".format(self.app.get('name')))
		icn=QtGui.QPixmap.fromImage(self.app.get('icon',''))
		self.lblIcon.setPixmap(icn.scaled(128,128))
		self.lblIcon.loadImg(self.app)
		self.lblSummary.setText("<h2>{}</h2>".format(self.app.get('summary')))
		self.lblDesc.setText(html.unescape(self.app.get('description')))
		self.lblDesc.setFixedWidth(self.height())#,self.height()/2)
		self.lblDesc.setFixedHeight(self.height()/3)#,self.height()/2)
		versions=self.app.get('versions',{})
		for bundle,name in self.app.get('bundle',{}).items():
			if bundle=="snap":
				self.btnSnap.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="snap" and state=='0':
						self.btnSnap.setText("{} snap".format(i18n.get("REMOVE")))
						self.btnSnap.setToolTip("{}".format(versions.get(bun,self.app.get('name'))))
			elif bundle=="flatpak":
				self.btnFlat.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="flatpak" and state=='0':
						self.btnFlat.setText("{} flatpak".format(i18n.get("REMOVE")))
						self.btnFlat.setToolTip("{}".format(versions.get(bun,self.app.get('name'))))
			elif bundle=="appimage":
				self.btnImage.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="appimage" and state=='0':
						self.btnImage.setText("{} appimage".format(i18n.get("REMOVE")))
						self.btnImage.setToolTip("{}".format(versions.get(bun,self.app.get('name'))))
			elif bundle=="package":
				self.btnApt.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="package" and state=='0':
						self.btnApt.setText("{} package".format(i18n.get("REMOVE")))
						self.btnApt.setToolTip("{}".format(versions.get(bun,self.app.get('name'))))
			elif bundle=="zomando":
				self.btnZomando.setVisible(True)
		homepage=self.app.get('homepage','')
		text=''
		if homepage:
			if homepage.endswith("/"):
				homepage=homepage[0,len(homepage)-1]
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
				self.Screenshot.addImage(icn)
		except Exception as e:
			print(e)
	#def _udpate_screen

	def _initScreen(self):
		cursor=QtGui.QCursor(Qt.PointingHandCursor)
		self.setCursor(cursor)
		self.Screenshot.clear()
		self.btnSnap.setText("{} snap".format(i18n.get("INSTALL")))
		self.btnImage.setText("{} appimage".format(i18n.get("INSTALL")))
		self.btnApt.setText("{} package".format(i18n.get("INSTALL")))
		self.btnFlat.setText("{} flatpak".format(i18n.get("INSTALL")))
		self.btnApt.setEnabled(False)
		self.btnApt.setToolTip("")
		self.btnFlat.setEnabled(False)
		self.btnFlat.setToolTip("")
		self.btnSnap.setEnabled(False)
		self.btnSnap.setToolTip("")
		self.btnImage.setEnabled(False)
		self.btnImage.setToolTip("")
		self.btnZomando.setVisible(False)
		self.lblSummary.setFixedWidth(self.height())
		self.lblHomepage.setText("")
		#self.lblDesc.setFixedWidth(self.height())
		#self.lblDesc.setFixedHeight(self.height()/2)
		#App is an argument from portrait. 
		#This call ensures all app data is loaded but it may take 1-2 seconds
		#self.app=json.loads(self.rc.execute('show',self.app.get('name')))[0]
		self.app['name']=self.app['name'].replace(" ","")
	#def _initScreen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

