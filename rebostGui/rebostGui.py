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


HLP_USAGE=_("usage: accesshelper [--set profile]|[--list]")
HLP_NOARGS=_("With no args launch accesshelper GUI")
HLP_SET=_("--set [profile]: Activate specified profile.\n\tCould be an absolute path or a profile from default profiles path")
HLP_LIST=_("--list: List available profiles")
ERR_WRKDIR=_("could not be accessed")
ERR_NOPROFILE=_("There's no profiles at")
ERR_LOADPROFILE=_("Error loading")
ERR_SETPROFILE=_("Must select one from:")
MSG_LOADPROFILE=_("Loading profile")
MSG_REBOOT=_("Changes will only apply after session restart")
MSG_LOGOUT=_("Logout")
MSG_CHANGES=_("Options selected:")
MSG_LATER=_("Later")
MSG_AUTOSTARTDISABLED=_("Profile not loaded: Autostart is disabled")
MSG_PROFILELOADED=_("Profile loaded")
TXT_ACCEPT=_("Close Session")
TXT_IGNORE=_("Ignore")
TXT_UNDO=_("Undo")

def showHelp():
	print(HLP_USAGE)
	print("")
	print(HLP_NOARGS)
	print(HLP_SET)
	print(HLP_LIST)
	print("")
	sys.exit(0)
#def showHelp():


##############
#### MAIN ####
##############

if len(sys.argv)==1:
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
