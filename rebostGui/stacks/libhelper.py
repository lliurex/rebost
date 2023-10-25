#!/usr/bin/python3
import os
import subprocess

class helper():
	def __init__(self):
		self.dbg=True
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("DBG: {}".format(msg))
	#def _debug

	def runZmd(self,app):
		zmdPath=os.path.join("/usr/share/zero-center/zmds",app.get('bundle',{}).get('zomando',''))
		if zmdPath.endswith(".zmd")==False:
			zmdPath="{}.zmd".format(zmdPath)
		if os.path.isfile(zmdPath):
			#Look if pkexec is needed
			appPath=os.path.join("/usr/share/zero-center/applications",app.get('bundle',{}).get('zomando','')).replace(".zmd",".app")
			if appPath.endswith(".app")==False:
				appPath="{}.app".format(appPath)
			cmd=[zmdPath]
			if os.path.isfile(appPath):
				with open (appPath,'r') as f:
					flines=f.readlines()
				for l in flines:
					if "pkexec" in l:
						cmd=["pkexec",zmdPath]
						break
			#subprocess.run(["pkexec",zmdPath])
			try:
				subprocess.run(cmd)
			except Exception as e:
				print(e)
				self.showMsg(e)
		else:
			self._zmdNotFound(zmdPath)

	def _zmdNotFound(self,zmd):
		def _launchZeroCenter():
			dlg.close()
			cmd=["zero-center"]
			try:
				subprocess.run(cmd)
			except Exception as e:
				print(e)
				self.showMsg(e)

		dlg=QDialog()
		dlg.setWindowTitle("Error")
		btns=QDialogButtonBox.Open|QDialogButtonBox.Cancel
		dlgBtn=QDialogButtonBox(btns)
		dlgBtn.accepted.connect(_launchZeroCenter)
		dlgBtn.rejected.connect(dlg.close)
		lay=QGridLayout()
		lbl=QLabel("{0}".format(i18n.get("ZMDNOTFOUND")))
		lay.addWidget(lbl)
		lay.addWidget(dlgBtn)
		dlg.setLayout(lay)
		dlg.exec()
	#def _zmdNotFound(self,zmd):

	def runApp(self,app,bundle): #TODO: QTHREAD
		#bundle=self.cmbOpen.currentText().lower().split(" ")[0]
		if bundle=="package":
			cmd=["gtk-launch",app.get("name",'')]
		elif bundle=="flatpak":
			cmd=["flatpak","run",app.get("bundle",{}).get("flatpak","")]
		elif bundle=="snap":
			cmd=["snap","run",app.get("bundle",{}).get("snap","")]
		elif bundle=="appimage":
			cmd=["gtk-launch","{}-appimage".format(app.get("name",''))]
		subprocess.run(cmd)