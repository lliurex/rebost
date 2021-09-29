#!/usr/bin/env python3
import rebostClient
import json
import os,sys
import subprocess
import time 

action=''
actionArgs=[]
swLoad=False


class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def _printInstall(result):
	if "-1" in result.keys():
		msg="Package {} it's available from different sources. Specify one to proceed\n".format(actionArgs[0])
		msg+="Package {} available as {}".format(actionArgs[0],list(result["-1"].keys()))
	else:
		pkg=result.get('package','unknown')
		if ';' in pkg:
			pkg=pkg.split(";")[0]
		msg=("Package {} {}".format(pkg,result.get('status','unknown')))
	return(msg)

def _printSearch(result):
	#msg=(f"{result['pkgname']} - {result['summary']}")
	msg=("{} - {}".format(result['pkgname'],result['summary']))
	if (result['bundle']):
		bundleStr=''
		for bundle in sorted(result['bundle'].keys()):
			if bundle=='appimage':
				bundleStr+=f" {color.DARKCYAN}appimage{color.END}"
			if bundle=='snap':
				bundleStr+=f" {color.RED}snap{color.END}"
			if bundle=='package' or bundle=="limba":
				bundleStr+=f" {color.YELLOW}package{color.END}"
			if bundle=='flatpak':
				bundleStr+=f" {color.PURPLE}flatpak{color.END}"

		msg=(f"{result['pkgname']} [{bundleStr} ] - {result['summary']}")
		msg=msg.rstrip("\n")
	return(msg)

def _printShow(result):
	#msg=f"Package: {result['pkgname']}\n"
	msg="Package: {}\n".format(result['pkgname'])
	bundleStr=''
	for bundle in sorted(result['bundle'].keys()):
		if bundle=='appimage':
			bundleStr+=f" {color.DARKCYAN}appimage{color.END}"
		if bundle=='snap':
			bundleStr+=f" {color.RED}snap{color.END}"
		if bundle=='package' or bundle=="limba":
			bundleStr+=f" {color.YELLOW}package{color.END}"
		if bundle=='flatpak':
			bundleStr+=f" {color.PURPLE}flatpak{color.END}"
	msg+=f"Format:{bundleStr}\n"
	versionStr=''
	for version in sorted(result['versions'].keys()):
		if version=='appimage':
			versionStr+=" {}{}{}".format(color.DARKCYAN,result['versions'].get('appimage'),color.END)
		if version=='snap':
			versionStr+=" {}{}{}".format(color.RED,result['versions'].get('snap'),color.END)
		if version=='package' or bundle=="limba":
			versionStr+=" {}{}{}".format(color.YELLOW,result['versions'].get('package'),color.END)
		if version=='flatpak':
			versionStr+=" {}{}{}".format(color.PURPLE,result['versions'].get('flatpak'),color.END)
	if versionStr=='':
			versionStr=result.get('version','unknown')
	msg+="Versions: {}\n".format(versionStr)
	cat=" ".join(result['categories'])
	msg+=f"Categories: {cat}\n"
	msg+=f"Availability: {result['installed']}\n"
	msg+="\n"
	msg+=f"{result['description']}"
	return(msg)

def printResults(proc=0):
	res=rebost.getResults(proc)
	for procId,procInfo in res.items():
		if 'result' in procInfo.keys():
			if procInfo['result']:
				try:
					for result in json.loads(procInfo['result']):
						msg=''
						if action=='search':
							msg=_printSearch(result)
						elif action=='show':
							msg=_printShow(result)
						elif action=='list':
							msg=_printSearch(result)
						elif action=='install' or action=='remove':
							if result.get('error',''):
								msg="%s %s %s: %s\n"%(action,result['name'],result['description'],result['errormsg'])
							else:
								msg="%s %s: %s\n"%(action,result['name'],result['description'])
						else:
							print(result)
						print(msg)
				except Exception as e:
					print()
					print("Results couldn't be processed: %s"%e)
					print(procInfo['result'])
			else:
				print(procInfo)
				print("Process error. %s failed"%(action.capitalize()))
		else:
			print("NO RESULTDATA")
		sys.exit(0)
#def printResults

def _loadStore():
	rebost.execute("load")
#def _loadStore

def _processArgs(*args):
	action=args[0]
	actionArgs=[]
	if len(action)>=2:
		if len(action)>2:
			actionArgs=args[0][2:]
		action=args[0][1]

	actionArgs=":".join(actionArgs)
	return(action,actionArgs)	

def _waitProcess(pid):
	var='LliureX Store'
	cont=1
	inc=1
	if os.path.exists("/proc/{}".format(pid)):

		fpid=os.fork()
		if fpid==0:
			os._exit(0)
		else:
			while (os.path.exists("/proc/{}".format(pid))):
				print("{} {}".format(var[0:cont],var[cont:]),end='\r')
				if cont>=len(var) or cont<=0:
					if cont<0:
						cont=0
					inc*=-1
				time.sleep(0.1)
				cont+=(inc)
		print("                           ",end='\r')

rebost=rebostClient.RebostClient()
#Set cli mode
rebost.execute('enableGui','false')
#_loadStore()
(action,actionArgs)=_processArgs(sys.argv)
#procList=[rebost.execute(action,actionArgs)]
#result=json.loads(str(rebost.execute(action,actionArgs)))
r=rebost.execute(action,actionArgs)
result=json.loads(rebost.execute(action,actionArgs))
	
if action=='search':
	for res in result:
		print(_printSearch(json.loads(res)))
if action=='show':
	for res in result:
		print(_printShow(json.loads(res)))
if action=='install':
	for res in result:
		pid=res.get('pid','-10')
		_waitProcess(pid)
		#print(_printInstall(res))
		print("Installed")
if action=='remove':
	for res in result:
		pid=res.get('pid','-10')
		_waitProcess(pid)
		print("Removed")

sys.exit(0)
sw=True
while sw:
	sw=False
	if not procList:
		time.sleep(0.5)
		continue
	for procId in procList:
		try:
			res=rebost.getProgress(procId)
		except Exception as e:
			print("Error connecting to D-Bus")
			print(e)
			break
		if res:
			for proc,procInfo in res.items():
				try:
					print("%s) %s %s %s"%(proc,procInfo['action']," ".join(actionArgs),procInfo['progress']),end="\r")
					if procInfo['progress']>=100:
						print("                                                            ",end="\r")
						printResults(procId)
					else:
						sw=True
				except Exception as e:
					print("Error %s: %s"%(proc,e))
				time.sleep(0.2)
		else:
			print("Failed to %s %s: Plugin disabled"%(action,actionArgs))
		time.sleep(0.5)
