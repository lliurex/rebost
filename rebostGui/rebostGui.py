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
gettext.textdomain('rebostGui')
_ = gettext.gettext

app=QApplication(["RebostGui"])
config=QStackedWindow()
icn=QtGui.QIcon.fromTheme("rebost")
config.setWindowIcon(icn)
config.disableNavBar(True)
if os.path.islink(__file__)==True:
	abspath=os.path.join(os.path.dirname(__file__),os.path.dirname(os.readlink(__file__)))
else:
	abspath=os.path.dirname(__file__)
config.addStacksFromFolder(os.path.join(abspath,"stacks"))
config.show()
config.setMinimumWidth(960)
config.setMinimumHeight(600)
if len(sys.argv)>1:
	if ("://") in sys.argv[1] or os.path.isfile(sys.argv[1]):
		config.setCurrentStack(3,parms=sys.argv[1])
app.exec_()
