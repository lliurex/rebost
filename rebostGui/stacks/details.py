#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QGridLayout,QTableWidget,QHeaderView,QHBoxLayout,QHBoxLayout
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSignalMapper,QSize,QThread,Signal
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appconfigControls
from rebost import store
import subprocess
import json
import random
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
	#def __init__

	def loadImg(self,app):
		img=app.get('icon','')
		self.scr=appconfigControls.loadScreenShot(img)
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
		self.box.addWidget(self.btnZomando,7,0,1,1,Qt.AlignTop)
		self.btnZomando.setVisible(False)
		self.btnApt.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnFlat.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnSnap.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnImage.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.btnZomando.setFixedSize(self.btnImage.sizeHint().width()+12, self.btnApt.sizeHint().height()+12)
		self.lblDesc.setFixedSize(self.height(),self.height()/2)
		self.Screenshot=appconfigControls.QScreenShotContainer()
		self.box.addWidget(self.Screenshot,8,0,1,2,Qt.AlignTop)
		self.setLayout(self.box)
	#def _load_screen

	def _installApt(self):
		pkg=self.app.get('name').replace(' ','')
		res=self.rc.execute('test',"{}:package".format(pkg))
		res=json.loads(res)[0]
		subprocess.run(["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')])
		self.updateScreen()
	#def _installApt

	def _installFlat(self):
		pkg=self.app.get('name').replace(' ','')
		res=self.rc.execute('test',"{}:flatpak".format(pkg))
		res=json.loads(res)[0]
		subprocess.run(["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')])
		self.updateScreen()
	#def _installFlat

	def _installSnap(self):
		pkg=self.app.get('name').replace(' ','')
		res=self.rc.execute('test',"{}:snap".format(pkg))
		res=json.loads(res)[0]
		subprocess.run(["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')])
		self.updateScreen()
	#def _installSnap

	def _installImage(self):
		pkg=self.app.get('name').replace(' ','')
		res=self.rc.execute('test',"{}:appimage".format(pkg))
		res=json.loads(res)[0]
		subprocess.run(["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')])
		self.updateScreen()
	#def _installImage

	def setParms(self,*args):
		self.app=args[0][0]

	def updateScreen(self):
		self._initScreen()
		self.lblName.setText("<h1>{}</h1>".format(self.app.get('name')))
		#icn=QtGui.QPixmap.fromImage(self.app.get('icon',''))
		#self.lblIcon.setPixmap(icn.scaled(128,128))
		self.lblIcon.loadImg(self.app)
		self.lblSummary.setText("<h2>{}</h2>".format(self.app.get('summary')))
		self.lblDesc.setText(self.app.get('description'))
		self.lblDesc.setFixedSize(self.height(),self.height()/2)
		for bundle,name in self.app.get('bundle',{}).items():
			if bundle=="snap":
				self.btnSnap.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="snap" and state=='0':
						self.btnSnap.setText("{} snap".format(i18n.get("REMOVE")))
			elif bundle=="flatpak":
				self.btnFlat.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="flatpak" and state=='0':
						self.btnFlat.setText("{} flatpak".format(i18n.get("REMOVE")))
			elif bundle=="appimage":
				self.btnImage.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="appimage" and state=='0':
						self.btnImage.setText("{} appimage".format(i18n.get("REMOVE")))
			elif bundle=="package":
				self.btnApt.setEnabled(True)
				for bun,state in self.app.get('state',{}).items():
					if bun=="package" and state=='0':
						self.btnApt.setText("{} package".format(i18n.get("REMOVE")))
			elif bundle=="zomando":
				self.btnZomando.setVisible(True)
		try:
			for icn in self.app.get('screenshots',[]):
				self.Screenshot.addImage(icn)
		except Exception as e:
			print(e)
	#def _udpate_screen

	def _initScreen(self):
		self.Screenshot.clear()
		self.btnSnap.setText("{} snap".format(i18n.get("INSTALL")))
		self.btnImage.setText("{} appimage".format(i18n.get("INSTALL")))
		self.btnApt.setText("{} package".format(i18n.get("INSTALL")))
		self.btnFlat.setText("{} flatpak".format(i18n.get("INSTALL")))
		self.btnApt.setEnabled(False)
		self.btnFlat.setEnabled(False)
		self.btnSnap.setEnabled(False)
		self.btnImage.setEnabled(False)
		self.btnZomando.setVisible(False)
		self.lblSummary.setFixedWidth(self.height())
		self.lblDesc.setFixedWidth(self.height())
		self.lblDesc.setFixedHeight(self.height()/2)
		self.app=json.loads(self.rc.execute('show',self.app.get('name')))[0]
		self.app=json.loads(self.app)
		self.app['name']=self.app['name'].replace(" ","")
	#def _initScreen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

