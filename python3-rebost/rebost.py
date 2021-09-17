#!/usr/bin/env python3
import rebostClient
import json
import os,sys
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
		print("Package {} it's available from different sources. Specify one to proceed".format(actionArgs[0]))
		print("Package {} available as {}".format(actionArgs[0],list(result["-1"].keys())))

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
	cat=" ".join(result['categories'])
	msg+=f"Categories: {cat}\n"
	msg+=f"Availability: {result['installed']}\n"
	if result['versions']:
		versionStr=''
		for bundle,version in sorted(result['versions'].items()):
			if bundle=='appimage':
				versionStr+=" {}{}{}".format(color.CYAN,version,color.END)
			if bundle=='snap':
				versionStr+=" {}{}{}".format(color.RED,version,color.END)
			if bundle=='package' or bundle=="limba":
				versionStr+=" {}{}{}".format(color.BOLD,version,color.END)
			if bundle=='flatpak':
				versionStr+=" {}{}{}".format(color.PURPLE,version,color.END)
		msg+=f"Version:{versionStr}\n"
	else:
		msg+=f"Version: {result['version']}\n"
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

	return(action,actionArgs)	

rebost=rebostClient.RebostClient()
#_loadStore()
(action,actionArgs)=_processArgs(sys.argv)
#procList=[rebost.execute(action,actionArgs)]
#result=json.loads(str(rebost.execute(action,actionArgs)))
result=json.loads(rebost.execute(action,actionArgs))
	
if action=='search':
	for res in result:
		print(_printSearch(json.loads(res)))
if action=='show':
	for res in result:
		print(_printShow(json.loads(res)))
if action=='install':
	for res in result:
		print(_printInstall(res))

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
