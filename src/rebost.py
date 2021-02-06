#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication
from appconfig.appConfigScreen import appConfigScreen as appConfig
app=QApplication(["Rebost"])
config=appConfig("Rebost",{'app':app})
config.setRsrcPath("/usr/share/rebost/rsrc")
config.setIcon('x-appimage')
config.setBanner('rebost.png')
config.setWiki('http://wiki.edu.gva.es/lliurex/tiki-index.php?page=rebost')
config.setBackgroundImage('drop_file.svg')
config.setConfig(confDirs={'system':'/usr/share/rebost','user':'%s/.config'%os.environ['HOME']},confFile="rebost.conf")
config.Show()
config.setFixedSize(config.width(),config.height())

app.exec_()
