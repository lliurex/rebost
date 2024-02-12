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

	def _getCmdFromZmd(self,zmdPath):
		#Look if pkexec is needed
		appPath=zmdPath.replace(".zmd",".app")
		appPath=appPath.replace("zmds/","applications/")
		if appPath.endswith(".app")==False:
			appPath="{}.app".format(appPath)
		cmd=[zmdPath]
		if os.path.isfile(appPath):
			with open (appPath,'r') as f:
				flines=f.readlines()
			for l in flines:
				if "pkexec" in l:
					cmd.insert(0,"pkexec")
					break
		return(cmd)
	#def _getCmdFromZmd

	def runZmd(self,app):
		ret=0
		zmdPath=os.path.join("/usr/share/zero-center/zmds",app.get('bundle',{}).get('zomando',''))
		if zmdPath.endswith(".zmd")==False:
			zmdPath="{}.zmd".format(zmdPath)
		if os.path.isfile(zmdPath):
			cmd=self._getCmdFromZmd(zmdPath)
			#subprocess.run(["pkexec",zmdPath])
			try:
				proc=subprocess.run(cmd)
				ret=proc.returncode
			except Exception as e:
				print(e)
				ret=-1
			if ret>0:
				#Zmd could depend on a zmd-installer so let's search
				zmdFolder=os.path.dirname(zmdPath)
				searchZmd=".".join(zmdPath.split(".")[:-1])
				newPath=zmdPath
				for f in os.scandir(zmdFolder):
					if searchZmd in f.path and f.path!=zmdPath:
						newPath=f.path
						break
				if zmdPath!=newPath:
					cmd=self._getCmdFromZmd(newPath)
					#subprocess.run(["pkexec",zmdPath])
					try:
						proc=subprocess.run(cmd)
					except Exception as e:
						print(e)
						ret=-1

			if ret>=0:
				ret=proc.returncode
		else:
			self._zmdNotFound(zmdPath)
		return(ret)
	#def runZmd

	def _zmdNotFound(self,zmd):
	#	def _launchZeroCenter():
	#		dlg.close()
		cmd=["zero-center"]
		try:
			subprocess.run(cmd)
		except Exception as e:
			print(e)

	#	dlg=QDialog()
	#	dlg.setWindowTitle("Error")
	#	btns=QDialogButtonBox.Open|QDialogButtonBox.Cancel
	#	dlgBtn=QDialogButtonBox(btns)
	#	dlgBtn.accepted.connect(_launchZeroCenter)
	#	dlgBtn.rejected.connect(dlg.close)
	#	lay=QGridLayout()
	#	lbl=QLabel("{0}".format(i18n.get("ZMDNOTFOUND")))
	#	lay.addWidget(lbl)
	#	lay.addWidget(dlgBtn)
	#	dlg.setLayout(lay)
	#	dlg.exec()
	#def _zmdNotFound(self,zmd):

	def runApp(self,app,bundle,launcher=""): #TODO: QTHREAD
		if len(launcher)>0:
			cmd=["gtk-launch",launcher]
		#bundle=self.cmbOpen.currentText().lower().split(" ")[0]
		elif bundle=="package":
			cmd=["gtk-launch",app.get("id",'')]
		elif bundle=="flatpak":
			cmd=["flatpak","run",app.get("bundle",{}).get("flatpak","")]
		elif bundle=="snap":
			cmd=["snap","run",app.get("bundle",{}).get("snap","")]
		elif bundle=="appimage":
			cmd=["gtk-launch","{}-appimage".format(app.get("name",''))]
		proc=subprocess.run(cmd)
		if proc.returncode!=0:
			cmd=["gtk-launch",app.get("name",'')]
			proc=subprocess.run(cmd)
		return(proc)
	#def runApp(self,app,bundle)
