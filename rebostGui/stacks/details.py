#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QApplication, QLabel, QPushButton,QGridLayout,QSizePolicy,QWidget,QComboBox,QDialog,QDialogButtonBox,QHBoxLayout,QListWidget,QVBoxLayout,QListWidgetItem
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal,QThread
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig import appconfigControls
from rebost import store
import subprocess
import json
import html
import gettext
from . import libhelper
_ = gettext.gettext
QString=type("")
R=140
G=255
B=0
A=70

i18n={
	"CONFIG":_("Details"),
	"DESCRIPTION":_("Show application detail"),
	"MENUDESCRIPTION":_("Navigate through all applications"),
	"TOOLTIP":_(""),
	"INSTALL":_("Install"),
	"CHOOSE":_("Choose"),
	"RUN":_("Open"),
	"REMOVE":_("Remove"),
	"UPGRADE":_("Upgrade"),
	"ZMDNOTFOUND":_("Zommand not found. Open Zero-Center?"),
	"FORMAT":_("Format"),
	"RELEASE":_("Release"),
	"ERRUNKNOWN":_("Unknown error")
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
			icn2=QtGui.QIcon.fromTheme(app.get('pkgname'))
			icn=icn2.pixmap(128,128)
		if icn:
			wsize=128
			if "Zomando" in app.get("categories","") or "zero" in app.get('pkgname',"").lower():
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
		self.dbg=False
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
		self.helper=libhelper.helper()
		self.epi=epiClass()
	#def __init__

	def _return(self):
		self.setWindowTitle("LliureX Store")
		self.stack.gotoStack(idx=1,parms="")
	#def _return

	def setParms(self,*args):
		swErr=False
		try:
			self.app=json.loads(args[0])
		except:
			swErr=True
		finally:
			if len(self.app)==0:
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
			self._return()
		else:
			self.setWindowTitle("LliureX Store - {}".format(self.app.get("name","")))
			for bundle,name in (self.app.get('bundle',{}).items()):
				if bundle=='package':
					continue
				name=self.app.get('name','')
				if name!='':
					status=self.rc.getAppStatus(name,bundle)
					self.app['state'][bundle]=str(status)
		cursor=QtGui.QCursor(Qt.PointingHandCursor)
		self.setCursor(cursor)
	#def setParms



	def _runZomando(self):
		self.helper.runZmd(self.app)
	#def _runZomando

	def _runApp(self):
		bundle=self.lstInfo.currentItem().text().lower().split(" ")[-1]
		self.helper.runApp(self.app,bundle)
	#def _runApp

	def _genericEpiInstall(self):
		bundle=self.lstInfo.currentItem().text().lower().split(" ")[-1]
		self.rc.enableGui(True)
		cursor=QtGui.QCursor(Qt.WaitCursor)
		self.setCursor(cursor)
		pkg=self.app.get('name').replace(' ','')
		user=os.environ.get('USER')
		res=self.rc.testInstall("{}".format(pkg),"{}".format(bundle),user=user)
		try:
			res=json.loads(res)[0]
		except:
			if isinstance(res,str):
				res=eval(res)[0]
				res=res[1]
				res['epi']=None
			else:
				res={}
		epi=res.get('epi')
		if epi==None:
			self.showMsg("{}".format(res.get('msg',i18n["ERRUNKNOWN"])))
			self.updateScreen()
		else:
			cmd=["pkexec","/usr/share/rebost/helper/rebost-software-manager.sh",res.get('epi')]
			self.epi.setArgs(self.app,cmd,bundle)
			self.epi.epiEnded.connect(self._getEpiResults)
			self.epi.start()
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

	def _load_screen(self):
		self.box=QGridLayout()
		self.btnBack=QPushButton()
		self.btnBack.setIcon(QtGui.QIcon.fromTheme("go-previous"))
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

		launchers=QWidget()
		lay=QHBoxLayout()
		self.btnInstall=QPushButton(i18n.get("INSTALL"))
		self.btnInstall.clicked.connect(self._genericEpiInstall)
		lay.addWidget(self.btnInstall,Qt.AlignLeft)
		self.btnRemove=QPushButton(i18n.get("REMOVE"))
		self.btnRemove.clicked.connect(self._genericEpiInstall)
		lay.addWidget(self.btnRemove,Qt.AlignLeft)

		self.btnZomando=QPushButton("{} zomando".format(i18n.get("RUN")))
		self.btnZomando.clicked.connect(self._runZomando)
		self.btnZomando.setVisible(False)
		lay.addWidget(self.btnZomando,Qt.AlignLeft)

		self.btnLaunch=QPushButton(i18n.get("RUN"))
		self.btnLaunch.clicked.connect(self._runApp)
		lay.addWidget(self.btnLaunch,Qt.AlignLeft)
		launchers.setLayout(lay)
		self.box.addWidget(launchers,2,0,1,3,Qt.AlignTop|Qt.AlignLeft)

		info=QWidget()
		layInfo=QHBoxLayout()
		info.setLayout(layInfo)
		self.lstInfo=QListWidget()
		self.lstInfo.currentRowChanged.connect(self._setLauncherOptions)	
		layInfo.addWidget(self.lstInfo)
		self.lblDesc=appconfigControls.QScrollLabel()
		self.lblDesc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.lblDesc.setWordWrap(True)	  
		layInfo.addWidget(self.lblDesc)
		self.box.addWidget(info,3,0,1,3)

		resources=QWidget()
		layResources=QVBoxLayout()
		resources.setLayout(layResources)
		self.lblHomepage=QLabel('<a href="http://lliurex.net">Homepage: lliurex.net</a>')
		self.lblHomepage.setOpenExternalLinks(True)
		self.screenShot=appconfigControls.QScreenShotContainer()
		self.screenShot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.screenShot.setStyleSheet("margin:0px;padding:0px;")
		layResources.addWidget(self.screenShot)
		layResources.addWidget(self.lblHomepage)
		self.box.addWidget(resources,4,0,1,3,Qt.AlignTop)
		self.box.setSpacing(0)
		self.setLayout(self.box)
		self.box.setColumnStretch(0,0)
		self.box.setColumnStretch(1,0)
		self.box.setColumnStretch(2,1)
		self.box.setRowStretch(3,1)
		self.box.setRowStretch(4,0)
	#def _load_screen

	def updateScreen(self):
		self._initScreen()
		self.lblName.setText("<h1>{}</h1>".format(self.app.get('name')))
		icn=self._getIconFromApp(self.app)
		self.lblIcon.setPixmap(icn.scaled(128,128))
		self.lblIcon.loadImg(self.app)
		self.lblSummary.setText("<h2>{}</h2>".format(self.app.get('summary','')))
		self.lblDesc.setText(html.unescape(self.app.get('description','').replace("***","\n")))
		versions=self.app.get('versions',{})
		bundles=list(self.app.get('bundle',{}).keys())
		self._updateScreenControls(bundles)
		homepage=self.app.get('homepage','')
		text=''
		if homepage:
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
		scrs=self.app.get('screenshots',[])
		if isinstance(scrs,list)==False:
			scrs=[]
		for icn in scrs:
			try:
				self.screenShot.addImage(icn)
			except Exception as e:
				print(e)
		self._setLauncherOptions()
	#def _updateScreen

	def _setLauncherOptions(self):
		item=self.lstInfo.currentItem()
		bundle=""
		rgb=(0,0,0,0)
		if item!=None:
			bundle=item.text().lower().split(" ")[-1]
			rgb=item.background().color().getRgb()
		if bundle=="package":
			bundle=""
		self.btnInstall.setText("{} {}".format(i18n.get("INSTALL"),bundle))
		self.btnRemove.setText("{} {}".format(i18n.get("REMOVE"),bundle))
		self.btnLaunch.setText("{} {}".format(i18n.get("RUN"),bundle))
		if rgb[0]==R and rgb[1]==G and rgb[2]==B and rgb[3]==A:
			self.btnInstall.setVisible(False)
			if self.app.get("bundle",{}).get("zomando","")!="":
				self.btnLaunch.setVisible(False)
				self.btnRemove.setVisible(False)
			else:
				self.btnRemove.setVisible(True)
				self.btnLaunch.setVisible(True)
			self.lstInfo.setStyleSheet("selection-color:grey;selection-background-color:rgba({0},{1},{2},0.5)".format(rgb[0],rgb[1],rgb[2]))
		else:
			pkgState=self.app.get('state',{}).get("package",'1')
			if pkgState.isdigit()==True:
				pkgState=int(pkgState)
			if pkgState==1 and self.app.get("bundle",{}).get("zomando","")!="":
				bundle="package"
				self.btnInstall.setText("{}".format(i18n.get("INSTALL")))
				self.lstInfo.setCurrentRow(1)
			self.lstInfo.setStyleSheet("")
			self.btnInstall.setVisible(True)
			self.btnRemove.setVisible(False)
			self.btnLaunch.setVisible(False)
	#def _setLauncherOptions


	def _getIconFromApp(self,app):
		icn=QtGui.QPixmap.fromImage(app.get('icon',''))
		if icn.depth()==0:
		#something went wrong. Perhaps img it's gzipped
			icn2=QtGui.QIcon.fromTheme(app.get('pkgname'))
			icn=icn2.pixmap(128,128)
		return(icn)
	#def _getIconFromApp

	def _updateScreenControls(self,bundles):
		pkgState=0
		if "zomando" in bundles:
			if "package" in bundles:
				pkgState=self.app.get('state',{}).get("package",'1')
				if pkgState.isdigit()==True:
					pkgState=int(pkgState)
				if pkgState==0:
					bundles.remove('package')
		states=0
		for bundle in bundles:
			state=(self.app.get('state',{}).get(bundle,'1'))
			if state.isdigit()==True:
				state=int(state)
			else:
				state=1
			states+=state
			if bundle=="zomando" and (pkgState==0 or state==0):
				self.btnZomando.setVisible(True)
				continue
			elif bundle=="zomando":
				continue
		self._getReleasesInfo()
	#def _updateScreenControls

	def _getReleasesInfo(self):
		bundles=self.app.get('bundle',[])
		self.lstInfo.clear()
		installed=[]
		uninstalled=[]
		priority=["zomando","snap","flatpak","appimage","package"]
		for bundle in bundles.keys():
			state=self.app.get("state",{}).get(bundle,1)
			if state.isdigit()==False:
				state="1"
			if int(state)==0: #installed
				installed.append(bundle)
			else:
				uninstalled.append(bundle)
		for p in priority:
			if p in installed:
				version=self.app.get('versions',{}).get(p,'')
				version=version.split("+")[0]
				release=QListWidgetItem("{} {}".format(version,p))
				release.setBackground(QtGui.QColor().fromRgb(R,G,B,A))
				self.lstInfo.addItem(release)
		for p in priority:
			if p in uninstalled:
				version=self.app.get('versions',{}).get(p,'')
				version=version.split("+")[0]
				release=QListWidgetItem("{} {}".format(version,p))
				self.lstInfo.addItem(release)
		if len(bundles)<=1 or "zomando" in bundles.keys():
			self.lstInfo.setVisible(False)
			if len(bundles)==1:
				if list(bundles.keys())[0]=="package":
					self.btnInstall.setText(i18n.get("INSTALL"))
				else:
					self.btnInstall.setText("{} {}".format(i18n.get("INSTALL"),list(bundles.keys())[0]))
			elif "zomando" in bundles.keys():
				self.lstInfo.setVisible(False)
				self.btnInstall.setVisible(False)
				self.btnLaunch.setVisible(False)
			else:
				self.btnInstall.setEnabled(False)
		else:
			self.lstInfo.setVisible(True)
		self.lstInfo.setMaximumWidth(self.lstInfo.sizeHintForColumn(0)+16)
		self.lstInfo.setCurrentRow(0)
	#def _getReleasesInfo

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
		self.btnInstall.setEnabled(True)
		self.btnInstall.setText(i18n.get("INSTALL"))
		self.setCursor(cursor)
		self.screenShot.clear()
		self.btnZomando.setVisible(False)
		self.lblHomepage.setText("")
		self.app['name']=self.app.get('name','').replace(" ","")
	#def _initScreen

	def _updateConfig(self,key):
		pass

	def writeConfig(self):
		return

