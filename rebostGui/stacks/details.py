#!/usr/bin/python3
import sys
import os
from PySide2.QtWidgets import QLabel, QPushButton,QGridLayout,QSizePolicy,QWidget,QComboBox,QDialog,QDialogButtonBox,QHBoxLayout,QListWidget,QVBoxLayout,QListWidgetItem,QGraphicsBlurEffect,QGraphicsOpacityEffect
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal,QThread
#from appconfig.appConfigStack import appConfigStack as confStack
from QtExtraWidgets import QScreenShotContainer,QScrollLabel,QStackedWindowItem
from app2menu import App2Menu as app2menu
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
	"APPUNKNOWN":_("The app could not be loaded. Until included in LliureX catalogue it can't be installed"),
	"CHOOSE":_("Choose"),
	"CONFIG":_("Details"),
	"DESC":_("Navigate through all applications"),
	"ERRLAUNCH":_("Error opening"),
	"ERRUNKNOWN":_("Unknown error"),
	"FORBIDDEN":_("App unauthorized"),
	"FORMAT":_("Format"),
	"INFO":_("For more info go to"),
	"INSTALL":_("Install"),
	"MENU":_("Show application detail"),
	"RELEASE":_("Release"),
	"REMOVE":_("Remove"),
	"RUN":_("Open"),
	"TOOLTIP":_("Details"),
	"UPGRADE":_("Upgrade"),
	"ZMDNOTFOUND":_("Zommand not found. Open Zero-Center?"),
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
			try:
				subprocess.run(["xhost","+"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
				proc=subprocess.run(self.args,stderr=subprocess.PIPE,universal_newlines=True)
				subprocess.run(["xhost","-"])
			except Exception as e:
				print(e)
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
		aux=QScreenShotContainer()
		self.scr=aux.loadScreenShot(img,self.cacheDir)
		icn=''
		if os.path.isfile(img):
			icn=QtGui.QPixmap.fromImage(img)
		elif img=='':
			icn2=QtGui.QIcon.fromTheme(app.get('pkgname'))
			icn=icn2.pixmap(128,128)
		if icn:
			wsize=128
			if "/usr/share/banners/lliurex-neu" in img:
				wsize=235
			self.setPixmap(icn.scaled(wsize,128,Qt.KeepAspectRatio,Qt.SmoothTransformation))
		elif img.startswith('http'):
			self.scr.start()
			self.scr.imageLoaded.connect(self.load)
	#def loadImg
	
	def load(self,*args):
		img=args[0]
		self.setPixmap(img.scaled(128,128))
	#def load
#class QLabelRebostApp

class details(QStackedWindowItem):
	def __init_stack__(self):
		self.dbg=False
		self._debug("details load")
		self.setProps(shortDesc=i18n.get("MENU"),
			longDesc=i18n.get("DESC"),
			icon="application-x-desktop",
			tooltip=i18n.get("TOOLTIP"),
			index=3,
			visible=True)
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
		self.oldcursor=self.cursor()
		self.appmenu=app2menu.app2menu()
		self.launcher=""
	#def __init__

	def _return(self):
		self.parent.setWindowTitle("LliureX Rebost")
		self.parent.setCurrentStack(1,parms={"refresh":True,"app":self.app})
	#def _return

	def _tagNav(self,*args):
		cat=args[0][0].replace("#","")
		self.parent.setWindowTitle("LliureX Rebost - {}".format(cat))
		self.parent.setCurrentStack(1,parms={"refresh":True,"cat":cat})

	def _processStreams(self,args):
		self.app={}
		if isinstance(args,str):
			name=""
			args=args.split("://")[-1]
			if args.startswith("install?"):
				ocs=args.split("&")[-1]
				idx=1
				for i in ocs.split("=")[-1]:
					if i.isalnum():
						idx+=1
					else:
						break
				name=ocs.split("=")[-1][:idx-1]
			else:
				name=args.replace(".desktop","").replace(".flatpakref","")
				name=name.split(".")[-1]
			if len(name)>0:
				app=self.rc.showApp(name)
				if len(app)>2:
					self.app=json.loads(app)[0]
					self.app=json.loads(self.app)
	#def _processStreams

	def setParms(self,*args):
		swErr=False
		try:
			self.app=json.loads(args[0])
		except Exception as e:
			print(e)
		if len(self.app)>0:
			if isinstance(self.app[0],str):
				try:
					self.app=json.loads(self.app[0])
				except Exception as e:
					print(e)
		if len(self.app)<=0:
			self._processStreams(args[0])
		else:
			self.parent.setWindowTitle("LliureX Rebost - {}".format(self.app.get("name","")))
			for bundle,name in (self.app.get('bundle',{}).items()):
				if bundle=='package':
					continue
				name=self.app.get('name','')
				if name!='':
					status=self.rc.getAppStatus(name,bundle)
					self.app['state'][bundle]=str(status)
		self.setCursor(self.oldcursor)
	#def setParms

	def _runZomando(self):
		self.helper.runZmd(self.app)
	#def _runZomando

	def _runApp(self):
		bundle=self.lstInfo.currentItem().text().lower().split(" ")[-1]
		proc=self.helper.runApp(self.app,bundle)
		if proc.returncode!=0:
			launcher=self._getLauncherForApp()
			proc=self.helper.runApp(self.app,bundle,launcher=launcher)
			if proc.returncode!=0:
				self.showMsg("{} {}".format(i18n.get("ERRLAUNCH"),self.app["name"]))
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

	def __initScreen__(self):
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
		layInfo=QGridLayout()
		info.setLayout(layInfo)
		self.lstInfo=QListWidget()
		self.lstInfo.currentRowChanged.connect(self._setLauncherOptions)	
		layInfo.addWidget(self.lstInfo,0,0,1,1)
		self.lblTags=QScrollLabel()
		self.lblTags.setStyleSheet("margin:0px;padding:0px;border:0px")
		layInfo.addWidget(self.lblTags,1,0,1,1)
		self.lblDesc=QScrollLabel()
		self.lblDesc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.lblDesc.setWordWrap(True)	  
		layInfo.addWidget(self.lblDesc,0,1,2,1)
		self.box.addWidget(info,3,0,1,3)

		resources=QWidget()
		layResources=QVBoxLayout()
		resources.setLayout(layResources)
		self.lblHomepage=QLabel('<a href="http://lliurex.net">Homepage: lliurex.net</a>')
		self.lblHomepage.setOpenExternalLinks(True)
		self.screenShot=QScreenShotContainer()
		self.screenShot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
		self.screenShot.setStyleSheet("margin:0px;padding:0px;")
		layResources.addWidget(self.screenShot)
		layResources.addWidget(self.lblHomepage)
		self.box.addWidget(resources,4,0,1,3,Qt.AlignTop)
		#self.box.setSpacing(0)
		self.setLayout(self.box)
		self.box.setColumnStretch(0,0)
		self.box.setColumnStretch(1,0)
		self.box.setColumnStretch(2,1)
		self.box.setRowStretch(3,1)
		self.box.setRowStretch(4,0)
		
		self.wdgError=QWidget()
		errorLay=QGridLayout()
		self.wdgError.setLayout(errorLay)
		self.lblBkg=QLabel(i18n.get("APPUNKNOWN"))
		errorLay.addWidget(self.lblBkg,0,0,1,1)
		self.wdgError.setVisible(False)
		self.box.addWidget(self.wdgError,1,0,self.box.rowCount()-1,self.box.columnCount())
	#def _load_screen

	def updateScreen(self):
		self._initScreen()
		self.lblName.setText("<h1>{}</h1>".format(self.app.get('name')))
		icn=self._getIconFromApp(self.app)
		self.lblIcon.setPixmap(icn.scaled(128,128))
		self.lblIcon.loadImg(self.app)
		self.lblSummary.setText("<h2>{}</h2>".format(self.app.get('summary','')))
		homepage=self.app.get('homepage','')
		bundles=list(self.app.get('bundle',{}).keys())
		if "eduapp" in bundles:
			self.app["description"]=i18n.get("APPUNKNOWN")
		text=''
		if homepage:
			homepage=homepage.rstrip("/")
			desc=homepage
			if len(homepage)>30:
				desc="{}...".format(homepage[0:30])
			text='<a href={0}>Homepage: {1}</a> '.format(homepage,desc)
			self.lblHomepage.setText(text)
		self.lblDesc.label.setOpenExternalLinks(False)
		description=html.unescape(self.app.get('description','').replace("***","\n"))
		if "FORBIDDEN" in self.app.get("categories",[]):
			description="<h2>{0}</h2>{1} <a href={2}>{2}</a><hr>\n{3}".format(i18n.get("FORBIDDEN"),i18n.get("INFO"),homepage,description)
			self.lblDesc.label.setOpenExternalLinks(True)
		self.lblDesc.setText(description)

		versions=self.app.get('versions',{})
		self._updateScreenControls(bundles)
		text=''
		applicense=self.app.get('license','')
		if applicense:
			text+="<strong>{}</strong>".format(applicense)
		
		scrs=self.app.get('screenshots',[])
		if isinstance(scrs,list)==False:
			scrs=[]
		if len(scrs)==0:
			self.screenShot.setVisible(False)
		else:
			self.screenShot.setVisible(True)
		for icn in scrs:
			try:
				self.screenShot.addImage(icn)
			except Exception as e:
				print(e)
		self._setLauncherOptions()
		tags=""
		for cat in self.app.get("categories",[]):
			tags+="<a href=\"#{0}\">{0}</a> ".format(_(cat))
		self.lblTags.setText(tags)
	#def _updateScreen

	def _getLauncherForApp(self):
		#Best effort for get launcher
		self.appmenu.set_desktop_system()
		cats=self.appmenu.get_categories()
		launcher=""
		for cat in cats:
			apps=self.appmenu.get_apps_from_category(cat.lower())
			for app in apps:
				appsplit=app.split(".")
				if len(appsplit)>2:
					searchapp=appsplit[-2]
				else:
					searchapp=appsplit[0]
				namesplit=self.app["pkgname"].split("-")
				allitems=namesplit+[searchapp]
				if len(allitems)!=len(set(allitems)):
					launcher=app
					break
			if len(launcher)>0:
				break
		return(launcher)
	#def _getLauncherForApp

	def _onError(self):
		self._debug("Error detected")
		qpal=QtGui.QPalette()
		color=qpal.color(qpal.Dark)
		#self.parent.setWindowTitle("LliureX Rebost - {}".format("ERROR"))
		#self.wdgError.setVisible(True)
		if "FORBIDDEN" not in self.app.get("categories",[]):
			self.app["categories"]=["FORBIDDEN"]
		#self.lstInfo.setVisible(False)
		#self.btnInstall.setVisible(False)
		#self.btnRemove.setVisible(False)
		#self.btnLaunch.setVisible(False)
		#self.blur=QGraphicsBlurEffect() 
		#self.blur.setBlurRadius(15) 
		#self.opacity=QGraphicsOpacityEffect()
		#self.lblBkg.setGraphicsEffect(self.blur)
		#self.lblBkg.setStyleSheet("QLabel{background-color:rgba(%s,%s,%s,0.7);}"%(color.red(),color.green(),color.blue()))
		#self.app["name"]=i18n.get("APPUNKNOWN").split(".")[0]
		#self.app["summary"]=i18n.get("APPUNKNOWN").split(".")[1]
		#self.app["pkgname"]="rebost"
		self.app["description"]=i18n.get("APPUNKNOWN")
	#def _onError

	def _setLauncherOptions(self):
		self.btnInstall.setEnabled(True)
		self.btnRemove.setEnabled(True)
		self.btnLaunch.setEnabled(True)
		self.btnZomando.setEnabled(True)
		bundle=""
		release=""
		tooltip=""
		item=self.lstInfo.currentItem()
		if item==None:
			print("Err: This app has not install option")
			self._onError()
			bundles=self.app.get("bundle",{})
			if len(bundles)>0:
				bundle=bundles.popitem()[1]
			else:
				bundle="package"
			self.lstInfo.insertItem(0,bundle)
			item=self.lstInfo.item(0)
			#return()
		bundle=item.text().lower().split(" ")[-1]
		release=item.text().lower().split(" ")[0]
		tooltip=item.text()
		self._setListState(item)
		if bundle=="package":
			bundle="app" # Only for show purposes. "App" is friendly than "package"
		if self.lstInfo.count()>0:
			self.btnInstall.setText("{0} {1}".format(i18n.get("INSTALL"),bundle))
			self.btnRemove.setText("{0} {1}".format(i18n.get("REMOVE"),bundle))
			self.btnLaunch.setText("{0} {1}".format(i18n.get("RUN"),bundle))
		self.btnInstall.setToolTip("{0}: {1}\n{2}".format(i18n.get("RELEASE"),release,bundle.capitalize()))
		self.btnRemove.setToolTip(tooltip)
		self.btnLaunch.setToolTip(tooltip)
		if "FORBIDDEN" in self.app.get("categories",[]) or "eduapp" in bundle:
			self.btnInstall.setEnabled(False)
			self.btnRemove.setEnabled(False)
			self.btnLaunch.setEnabled(False)
			self.btnZomando.setEnabled(False)
	#def _setLauncherOptions

	def _setListState(self,item):
		bcurrent=item.background().color()
		bcolor=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Inactive,QtGui.QPalette.Dark)).toRgb()
		if bcurrent==bcolor:
			rgb=bcurrent.getRgb()
			self.btnInstall.setVisible(False)
			if self.app.get("bundle",{}).get("zomando","")!="":
				self.btnLaunch.setVisible(False)
				if "zomando" in item.text():
					self.btnRemove.setVisible(False)
				else:
					self.btnRemove.setVisible(True)
			else:
				self.btnRemove.setVisible(True)
				self.btnLaunch.setVisible(True)
			self.lstInfo.setStyleSheet("selection-color:grey;selection-background-color:rgba({0},{1},{2},0.5)".format(rgb[0],rgb[1],rgb[2]))
		else:
			pkgState=self.app.get('state',{}).get("package",'1')
			if pkgState.isdigit()==True:
				pkgState=int(pkgState)
			else:
				self._onError()
				return()
	#		if pkgState==1 and self.app.get("bundle",{}).get("zomando","")!="":
		#		self.btnInstall.setText("{}".format(i18n.get("INSTALL")))
	#			self.lstInfo.setCurrentRow(1)
			self.lstInfo.setStyleSheet("")
			self.btnInstall.setVisible(True)
			self.btnRemove.setVisible(False)
			self.btnLaunch.setVisible(False)
	#def _setLstState

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
		states=0
		self.btnZomando.setVisible(False)
		for bundle in bundles:
			state=(self.app.get('state',{}).get(bundle,'1'))
			if state.isdigit()==True:
				state=int(state)
			else:
				state=1
			states+=state
			if bundle=="zomando" and ((pkgState==0 or state==0) or (self.app.get("pkgname","x$%&/-1") not in self.app["bundle"]["zomando"])):
				self.btnZomando.setVisible(True)
				continue
		#	elif bundle=="zomando":
		#		continue
		self._setReleasesInfo()
	#def _updateScreenControls

	def _setReleasesInfo(self):
		bundles=self.app.get('bundle',[])
		self.lstInfo.clear()
		if isinstance(bundles,dict)==False:
			return()
		(installed,uninstalled)=self._classifyBundles(bundles)
		priority=["zomando","snap","flatpak","appimage","package","eduapp"]
		for i in installed+uninstalled:
			version=self.app.get('versions',{}).get(i,'')
			version=version.split("+")[0]
			if version=="":
				version="lliurex23"
			release=QListWidgetItem("{} {}".format(version,i))
			if i in priority:
				idx=priority.index(i)
				if i in uninstalled:
					idx+=len(installed)
				else:
					#bcolor=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Active,QtGui.QPalette.AlternateBase))
					bcolor=QtGui.QColor(QtGui.QPalette().color(QtGui.QPalette.Inactive,QtGui.QPalette.Dark))
					release.setBackground(bcolor)
				self.lstInfo.insertItem(idx,release)
		if "eduapp" in bundles.keys():
			bundles.pop("eduapp")
		if len(bundles)<=0:
			self.btnInstall.setEnabled(False)
		self.lstInfo.setMaximumWidth(self.lstInfo.sizeHintForColumn(0)+16)
		self.lstInfo.setCurrentRow(0)
		self.lblTags.setMaximumWidth(self.lstInfo.sizeHintForColumn(0)+16)
	#def _setReleasesInfo

	def _classifyBundles(self,bundles):
		installed=[]
		uninstalled=[]
		for bundle in bundles.keys():
			state=self.app.get("state",{}).get(bundle,1)
			if bundle=="zomando":
				if "package" in bundles.keys():
					continue
				if os.path.isfile(bundles[bundle]):
					state="0"
			if state.isdigit()==False:
				state="1"
			if int(state)==0: #installed
				installed.append(bundle)
			else:
				uninstalled.append(bundle)
		return(installed,uninstalled)
	#def _classifyBundles

	def _initScreen(self):
		#Reload config if app has been epified
		if len(self.app)>0:
			self.wdgError.setVisible(False)
			self.lstInfo.setVisible(True)
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
			self.btnInstall.setEnabled(True)
			self.btnInstall.setText(i18n.get("INSTALL"))
			self.setCursor(self.oldcursor)
			self.screenShot.clear()
			self.btnZomando.setVisible(False)
			self.lblHomepage.setText("")
			self.lblTags.setText("")
			self.lblTags.linkActivated.connect(self._tagNav)
			self.app['name']=self.app.get('name','').replace(" ","")
		else:
			self._onError()
	#def _initScreen

	def _updateConfig(self,key):
		print(key)
		pass

	def writeConfig(self):
		return

