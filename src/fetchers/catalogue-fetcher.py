#!/usr/bin/python3
import sys,json,time,os
import gi
from gi.repository import Gio
gi.require_version('AppStream', '1.0')
from gi.repository import AppStream as appstream
from urllib.request import Request,urlopen
from aux._plugins import _fetcherPlugins

def _log(msg):
	t=time.localtime()
	date="{0:02d}{1:02d}{2:02d} {3:02d}{4:02d}{5:02d}".format(t.tm_year,t.tm_mon,t.tm_mday,t.tm_hour,t.tm_min,t.tm_sec)
	print("{0} {1}".format(date,msg))
#def _log

def _help():
	print("Usage: ")
	print("  {} [OPTION]".format(sys.argv[0]))
	print("\nAvailable options:")
	print("  -l|--list: show supported releases")
	print("  release: generate catalogue for release")
	print("  -lf|--list-formats: show supported formats")
	print("  -d [format]|--disable [format]: don't generate catalogue for [format]")
	print()
	print("Example:")
	print("  {} llx25: Generates full catalogue for llx25".format(sys.argv[0]))
	print()
	sys.exit(0)
#def _help

def _loadPlugins(store):
	loader=_fetcherPlugins()
	return(loader.loadPlugins(store))
#def _loadPlugins():

def _getReleases():
	return(config.keys())

def _listReleases():
	print("\nSupported releases:")
	for release in _getReleases():
		print("- {}".format(release))
	print()
#def _listReleases

def _listFormats():
	print("\nSupported formats:")
	for plugin in supportedFormats:
		if plugin!=None:
			print("- {}".format(plugin.to_string(plugin).capitalize()))
	print()
#def _listFormats

def _readConfig():
	config={}
	with open("fetcher.conf","r") as f:
		config=json.load(f)
	return(config)
#def _readConfig

def _processArgs():
	global release
	die=False
	args=sys.argv[1:]
	if len(args)==0:
		print()
		_help()
	while args:
		arg=args.pop().replace("-","")
		if arg in ["l","list"]:
			_listReleases()
			die=True
		elif arg in ["lf","listformats"]:
			_listFormats()
			die=True
		elif arg in ["d","disable"]:
			disable=args.pop()
		else:
			if arg not in _getReleases():
				print("\nRelease {} unsupported".format(arg))
				_listReleases()
				print("Try «{} --help» for more information".format(sys.argv[0]))
				print()
				die=True
			release=arg
	if die==True:
		sys.exit(0)
#def _processArgs

def _getMapFile(mapUrl):
	content={}
	urlContent=""
	if mapUrl!="" and isinstance(mapUrl,str):
		req=Request(mapUrl, headers={'User-Agent':'Mozilla/5.0'})
		try:
			with urlopen(req,timeout=2) as f:
				urlContent=(f.read().decode('utf-8'))
		except Exception as e:
			self._debug("Couldn't fetch {}".format(mapUrl))
			self._debug(e)
	if len(urlContent)>0:
		try:
			content=json.loads(urlContent)
		except Exception as e:
			print(e)
			content={}
	return(content)
#def _getMapFile

def _generateCatalogueByPrioriy(mapping,plugin):
	_log("Getting catalogues with priority {0}: {1}".format(plugin,list(plugins[plugin].keys())))
	for plugName,fetcher in plugins[plugin].items():
		if isinstance(plugName,str)==False:
			plugName=plugName.to_string(plugName)
		_log("Processing {}".format(plugName))
		metadata=fetcher[0].fetchCatalogue(mapping)
		fxml="{}.dep11.xml".format(plugName)
		_log("Generate {}/{}".format(metaFolder,fxml))
		metadata.save_catalog(os.path.join(metaFolder,fxml),appstream.FormatKind.XML)
#def _generateCatalogueByPrioriy

def _fetchCatalogues():
	_log("Getting map files for {}".format(release))
	mapping=_getMapFile(mapUrl)
	#Fetch by priority
	priority=list(plugins.keys())
	priority.sort()
	priority.reverse()
	for plugin in priority:
		_generateCatalogueByPrioriy(mapping,plugin)
	_log("All info processed")
#def _fetchCatalogues

def _mergeCatalogues():
	fxml="{}.dep11.xml".format(release)
	store.save_catalog(os.path.join(metaFolder,"xml",fxml),appstream.FormatKind.XML)


def _loadCatalogues():
	_log("Loading generated appstream data from {}".format(metaFolder))
	pool=appstream.Pool()
	pool.set_load_std_data_locations(False)
	pool.add_extra_data_location(metaFolder,appstream.FormatStyle.CATALOG)
	pool.load()
	_log("Loaded {} apps".format(pool.get_components().get_size()))
	return(pool)
#def _loadCatalogues():

def _beginProcess():
	xmlFolder=os.path.join(metaFolder,"xml")
	iconsFolder=os.path.join(metaFolder,"icons")
	for d in [metaFolder,xmlFolder,iconsFolder]:
		if os.path.exists(d)==False:
			os.makedirs(d)
#def _beginProcess

release=""
store=appstream.Metadata()
store.set_update_existing(True)
store.set_format_version(appstream.FormatVersion.V1_0)
config=_readConfig()
supportedFormats,plugins=_loadPlugins(store)
_processArgs()
mapUrl=config[release]["upstream"]
metaFolder=config[release]["metafolder"]
store.set_origin(release)
_beginProcess()
_fetchCatalogues()
_mergeCatalogues()
pool=_loadCatalogues()
test=pool.get_components_by_id("ocrfeeder")
for app in test.as_array():
	b=app.to_xml_data(appstream.Context())
	print(b)

	
