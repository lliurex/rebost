#!/usr/bin/env python3
import sys
import subprocess
import os,shutil
import json
from PySide2.QtWidgets import QApplication,QDialog,QGridLayout,QLabel,QPushButton,QLayout,QSizePolicy,QDesktopWidget
from PySide2.QtCore import Qt
from PySide2 import QtGui
from appconfig.appConfigScreen import appConfigScreen as appConfig
from appconfig import appconfigControls
import gettext
import time
_ = gettext.gettext

app=QApplication(["RebostGui"])
config=appConfig("RebostGui",{'app':app})
config.setWindowTitle("Lliurex Store")
config.setRsrcPath("/usr/share/rebost/rsrc")
config.setIcon('rebost')
config.setWiki('https://wiki.edu.gva.es/lliurex/tiki-index.php?page=Accesibilidad%20en%20Lliurex:%20Access%20Helper')
config.setBanner('rebost_banner.svg')
config.hideNavMenu(True)
#config.setBackgroundImage('repoman_login.svg')
config.setConfig(confDirs={'system':'/usr/share/rebost','user':os.path.join(os.environ['HOME'],".config/rebost")},confFile="store.json")
config.Show()
sizeObject = QDesktopWidget().screenGeometry(-1)
config.resize(int(sizeObject.width()/1.75),int(sizeObject.height()/1.40)+16)
app.exec_()
