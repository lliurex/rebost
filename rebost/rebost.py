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
   GREEN = '\033[32m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def _printInstall(result,pid):
	status=_getResult(pid)
	if status.lower()!='unknown' and str(status).isnumeric()==False:
		pkg=result.get('package','unknown')
		if ';' in pkg:
			pkg=pkg.split(";")[0]
		msg=("Package {0} {1}{2}{3}".format(pkg,color.UNDERLINE,status,color.END))
	else:
		msg="{0}Error:{1} {2} {3}".format(color.RED,color.END,actionArgs,result.get('msg',''))
	return(msg)

def _printSearch(result):
	#msg=(f"{result['pkgname']} - {result['summary']}")
	msg=("{} - {}".format(result['pkgname'],result['summary']))
	if (result['bundle']):
		bundleStr=''
		for bundle in sorted(result['bundle'].keys()):
			state=''
			if result['state'].get(bundle,'')=="0":
				state='*'

			if bundle=='appimage':
				bundleStr+=f" {color.PURPLE}appimage{state}{color.END}"
			if bundle=='snap':
				bundleStr+=f" {color.RED}snap{state}{color.END}"
			if bundle=='package' or bundle=="limba":
				bundleStr+=f" {color.YELLOW}package{state}{color.END}"
			if bundle=='flatpak':
				bundleStr+=f" {color.BLUE}flatpak{state}{color.END}"

		msg=(f"{result['pkgname']} [{bundleStr} ] - {result['summary']}")
		msg=msg.rstrip("\n")
	return(msg)

def _printShow(result):
	#msg=f"Package: {result['pkgname']}\n"
	msg="Package: {}\n".format(result['pkgname'])
	bundleStr=''
	for bundle in sorted(result['bundle'].keys()):
		state=''
		if result['state'].get(bundle,'')=="0":
			state='*'
		if bundle=='appimage':
			bundleStr+=f" {color.PURPLE}appimage{state}{color.END}"
		if bundle=='snap':
			bundleStr+=f" {color.RED}snap{state}{color.END}"
		if bundle=='package' or bundle=="limba":
			bundleStr+=f" {color.YELLOW}package{state}{color.END}"
		if bundle=='flatpak':
			bundleStr+=f" {color.BLUE}flatpak{state}{color.END}"
	msg+=f"Format:{bundleStr}\n"
	versionStr=''
	for version in sorted(result['versions'].keys()):
		if version=='appimage':
			versionStr+=" {}{}{}".format(color.PURPLE,result['versions'].get('appimage'),color.END)
		if version=='snap':
			versionStr+=" {}{}{}".format(color.RED,result['versions'].get('snap'),color.END)
		if version=='package' or bundle=="limba":
			versionStr+=" {}{}{}".format(color.YELLOW,result['versions'].get('package'),color.END)
		if version=='flatpak':
			versionStr+=" {}{}{}".format(color.BLUE,result['versions'].get('flatpak'),color.END)
	if versionStr=='':
			versionStr=result.get('version','unknown')
	msg+="Versions: {}\n".format(versionStr)
	cat=" ".join(result['categories'])
	msg+=f"Categories: {cat}\n"
	msg+="\n"
	msg+=f"{result['description']}"
	return(msg)

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
	var='LliureX Store '
	var2=var
	cont=1
	inc=1
	data={}
	done=None
	for proc in rebost.getResults():
		(ppid,pdata)=proc
		if str(ppid)==str(pid):
			if isinstance(pdata,str):
				data=json.loads(pdata)
			elif isinstance(pdata,dict):
				data=pdata.copy()
			break
	if data:
		while done==None:
			done=data.get('done')
			print("{} {}".format(var[0:cont],var[cont:]),end='\r')
			if cont>=len(var) or cont<=0:
				if cont<=0:
					cont=1
				else:
					percentage=0
					perc=data.get('status',0)
					if isinstance(perc,str):
						if perc.isnumeric():
							percentage=int(perc)
					elif isinstance(perc,int):
						percentage=perc
					if percentage>0:
						print('{} {} {}%'.format(var[0:cont],var[cont:],perc),end='\r')
				inc*=-1
			time.sleep(0.1)
			cont+=(inc)
			for proc in rebost.getResults():
				(ppid,pdata)=proc
				if str(ppid)==str(pid):
					if isinstance(pdata,str):
						data=json.loads(pdata)
					elif isinstance(pdata,dict):
						data=pdata.copy()
					break
		per=int(data.get('status',0))
		while per<=100:
			print('{} {} {}%'.format(var[0:cont],var[cont:],per),end='\r')
			per+=1
			time.sleep(0.01)
		time.sleep(0.2)
	print("                                ",end='\r')

def _getResult(pid):
	status='Unknown'
	result=status
	for proc in rebost.getResults():
		(ppid,data)=proc
		if isinstance(data,str):
			data=json.loads(data)
		if str(ppid)==str(pid):
			try:
				status=data.get('status',-2)
			except Exception as e:
				print(data)
				print(e)
			if status=='0':
				result="installed"
			elif status=='1':
				result="removed"
			elif status=='-1':
				result="an {}error{} ocurred when attempting to {}".format(color.RED,color.END,action)
			else:
				result="unknown status {}".format(status)
	return(result)

def showHelp():
	if "help" not in action:
		print("Unknown option {}".format(action))
	print("Usage:")
	print("\trebost action query format(optional)")
	print("\trebost search|show|install|remove pkgname [format]")
	print()
	print("s | search: Searchs packages using pkgname as query")
	print("show: Shows info related to one package")
	print("i | install: Install one package. If package comes from many formats one must be specified")
	print("r | remove: Remove one package. If package comes from many formats one must be specified")
	print()
	print("Examples:")
	print("\t*Install firefox-esr as appimage: rebost install firefox-esr appimage")
	print("\t*Remove chromium snap: rebost remove chromium")
	print("\t*Show info related to zero-center: rebost show zero-center")
	print("\t*Search for packages containing \"prin\": rebost search prin")

rebost=rebostClient.RebostClient(user=os.getenv('USER'))
#Set cli mode
rebost.execute('enableGui','false')
(action,actionArgs)=_processArgs(sys.argv)
action=action.replace("-","")
#procList=[rebost.execute(action,actionArgs)]
#result=json.loads(str(rebost.execute(action,actionArgs)))
result=json.loads(rebost.execute(action,actionArgs))
	
if action=='search' or action=='s':
	for res in result:
		print(_printSearch(json.loads(res)))
elif action=='show':
	for res in result:
		if isinstance(res,dict):
			print(_printShow(res))
		else:
			print(_printShow(json.loads(res)))
elif action in ["install","i","remove","r"]:
	for res in result:
		if isinstance(res,str):
			res=json.loads(res)
		pid=res.get('pid','-10')
		_waitProcess(pid)
		print(_printInstall(res,pid))
elif action=='test':
	print(result)
else:
	showHelp()

sys.exit(0)
