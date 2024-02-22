#!/usr/bin/env python3
import sys
import subprocess
import os,shutil
import json
from PySide2.QtWidgets import QApplication,QDialog,QGridLayout,QLabel,QPushButton,QLayout,QSizePolicy,QDesktopWidget
from PySide2.QtCore import Qt
from PySide2 import QtGui
from QtExtraWidgets import QStackedWindow
import gettext
import time
gettext.textdomain('rebostgui')
_ = gettext.gettext

app=QApplication(["LliureX Rebost"])
mw=QStackedWindow()
icn=QtGui.QIcon.fromTheme("rebost")
mw.disableNavBar(True)
mw.setWindowIcon(icn)
if os.path.islink(__file__)==True:
	abspath=os.path.join(os.path.dirname(__file__),os.path.dirname(os.readlink(__file__)))
else:
	abspath=os.path.dirname(__file__)
mw.addStacksFromFolder(os.path.join(abspath,"stacks"))
mw.show()
mw.setMinimumWidth(960)
mw.setMinimumHeight(600)
if len(sys.argv)>1:
	if ("://") in sys.argv[1] or os.path.isfile(sys.argv[1]):
		mw.setCurrentStack(3,parms=sys.argv[1])
app.exec_()
