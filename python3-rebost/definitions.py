#!/usr/bin/env python3
import os
import html2text
	
def rebostProcess(*kwargs):
	reb={'plugin':'','kind':'','progressQ':'','progress':'','resultQ':'','result':'','action':'','parm':'','proc':''}
	return(reb)

def resultSet(*kwargs):
	rs={'id':'','name':'','title':'','msg':'','description':'','error':0,'errormsg':''}
	return(rs)

def rebostPkg(*kwargs):
	pkg={'name':'','id':'','size':'','screenshots':[],'video':[],'pkgname':'','description':{},'summary':{},'icon':'','size':'','downloadSize':'','bundle':{},'kind':'','version':'','versions':{},'installed':'','banner':'','license':'','homepage':'','categories':[],'installerUrl':'','state':{}}
	return(pkg)

def rebostPkgList_to_xml(rebostPkgList,xmlFile):
	if not os.path.exists(os.path.dirname(xmlFile)):
		try:
			os.makedirs(os.path.dirname(xmlFile))
		except:
			print("Error creating folder {}".format(xmlFile))
			rebostPkgList=[]

	for rebost in rebostPkgList:
		f_file=os.path.join(os.path.dirname(xmlFile),"{}.xml".format(rebost['id']))
		_generateInfo(f_file,rebost)


def _sanitizeString(data):
	if isinstance(data,str):
		data=html2text.html2text(data,"lxml")
		data=data.replace("&","and")
		data=data.replace("\n"," ")
		data=data.replace("<","*")
		data=data.replace(">","*")
		data=data.replace("\\","*")
		data=data.replace("<p><p>","<p>")
		data=data.replace("*br*"," ")
		data=data.replace("*p*"," ")
		data=data.replace('<\p><\p>','<\p>')
	return(data)


def _generateInfo(f_file,rebost):
	locale="C"
	f_list=[]
	f_list=['<?xml version="1.0" encoding="UTF-8"?>']
	f_list.append('<components>')
	f_list.append('<component type="desktop">')
	f_list.append('<id>{}</id>'.format(rebost['id'].lower()))
	f_list.append('<name>{}</name>'.format(rebost['name']))
	f_list.append('<pkgname>{}</pkgname>'.format(rebost['pkgname']))
	if isinstance(rebost['summary'],dict):
		for lang,desc in rebost['summary'].items():
			desc=_sanitizeString(rebost['summary'][lang])
			f_list.append("<summary xml:lang=\"{}\" >{}</summary>".format(lang.lower(),desc))
		idx=rebost['summary'].get("C",'')
		if idx:
			desc=_sanitizeString(rebost['summary']["C"])
			f_list.append("<summary>{}</summary>".format(desc))
		else:
			idx=list(rebost['summary'].keys())[0]
			desc=_sanitizeString(rebost['summary'][idx])
			f_list.append("<summary>{}</summary>".format(desc))
	else:
		desc=_sanitizeString(rebost['summary'])
		f_list.append("<summary>{}</summary>".format(desc))
	if isinstance(rebost['description'],dict):
		for lang,desc in rebost['description'].items():
			desc=_sanitizeString(rebost['description'][lang])
			f_list.append("<description xml:lang=\"{}\" ><p>{}</p></description>".format(lang.lower(),desc))
		idx=rebost['description'].get("C",'')
		if idx:
			f_list.append("<description><p>{}</p></description>".format(_sanitizeString(rebost['description']["C"])))
		elif rebost['description']:
			idx=list(rebost['description'].keys())[0]
			f_list.append("<description><p>{}</p></description>".format(_sanitizeString(rebost['description'][idx])))
	else:
		desc=_sanitizeString(html2text.html2text(rebost['description'],"lxml"))
		f_list.append("<description><p>{}</p></description>".format(desc))
	if rebost['icon'] and os.path.isfile(rebost['icon']):
		f_list.append('<icon type="local">{}</icon>'.format(rebost['icon']))
	else:
		f_list.append('<icon type="stock">{}</icon>'.format(rebost['icon']))
	#f_list.append('<kind>{}</kind>'.format(rebost['kind']))
	f_list.append('<categories>')
	added_cat=[]
	for cat in rebost['categories']:
		if cat and cat.lower() not in added_cat:
			f_list.append('<category>{}</category>'.format(cat))
			added_cat.append(cat.lower())
	if not added_cat:
		f_list.append('<category>Utility</category>')
	f_list.append('</categories>')
	xstatus={}
	if rebost["bundle"]:
		bundlePkg=''
		if rebost['installerUrl']:
				#bundlePkg=rebost['installerUrl']
			f_list.append('<url type="unknown">{}</url>'.format(rebost['installerUrl']))
		for bundle,desc in rebost["bundle"].items():
			if bundlePkg=='':
				bundlePkg=desc
			f_list.append("<bundle type=\"{}\">{}</bundle>".format(bundle,bundlePkg))

	if rebost['homepage']:
		f_list.append('<url type="homepage">{}</url>'.format(rebost['homepage']))
	if rebost['version']:
		f_list.append("<releases><release version=\"{}\"/></releases>".format(rebost["version"]))

	f_list.append('</component>')
	f_list.append('</components>')
	try:
		with open(f_file,'w') as f:
			f.writelines(f_list)
	except Exception as e:
		print("File {} error:{}".format(f_file,e))
