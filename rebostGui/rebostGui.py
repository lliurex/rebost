#!/usr/bin/env python3
import sys
import subprocess
import os,shutil
import json
from PySide2.QtWidgets import QApplication,QDialog,QGridLayout,QLabel,QPushButton,QLayout,QSizePolicy
from PySide2.QtCore import Qt
from PySide2 import QtGui
from appconfig.appConfigScreen import appConfigScreen as appConfig
from appconfig import appconfigControls
import gettext
import time
_ = gettext.gettext
gettext.textdomain('lliurex-store')

app=QApplication(["Lliurex-Store"])
config=appConfig("Lliurex Store",{'app':app})
config.setWindowTitle("Lliurex Store")
config.setRsrcPath("/usr/share/lliurexstore/rsrc")
config.setIcon('lliurexstore')
config.setWiki('https://wiki.edu.gva.es/lliurex/tiki-index.php?page=Accesibilidad%20en%20Lliurex:%20Access%20Helper')
config.setBanner('access_banner.png')
config.hideNavMenu(True)
#config.setBackgroundImage('repoman_login.svg')
config.setConfig(confDirs={'system':'/usr/share/lliurexstore','user':os.path.join(os.environ['HOME'],".config/lliurexstore")},confFile="store.json")
config.Show()
#config.setFixedSize(config.width(),config.height())
app.exec_()
