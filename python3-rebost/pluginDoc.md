!#Plugin Doc

A plugin adds functionality to rebost. It can be specific for a kind of package and can define some autostart actions. Needs a main class named as the module.py (ex: plugin.py must implement the class *plugin*)

!!# Commom methods

A pluging must define some methods in order to work within rebost:

!!!#getPackageType
def getPackageType()
	return(str(package_type))

!!!#getAction
def getAction():
	return([action])

!!!#getAutostart
def getAutostart():
	return([action])

!!!#getState
def getState():
	return({action:bool(enabled)})

!!!#getProgress
	return({transactionID:int(progress))

!!!#setState
	def setState({action:str(state)}):
		return (bool(ok))

!!!#setHold
	def setHold({int(transactionID):bool(hold)):
		return (bool(ok))

!!!#restart
	def restart():
		return(bool(ok))

!!!#executeAction(str(action)):
	def executeAction:
		return(int(transactionID))

!!!#cancelTransaction():
	def cancelTransaction(int(transactionID)):
		return(bool(ok))

!!#Common Attributes

Mandatory attributes

__bool(enable)__: False/True
__str(packageType)__: Package format supported by the plugin (packageKit,zomando,air,appimage,snap,script,all...)
__list(actions)__: Actions that provides the plugin (install, search,..etc..)
__dict(transaction:progress)__: Dict that contains the progress for each transaction
__dict(transaction:state)__: Dict that containts the state of each translation (one of [enabled/holded/disabled])

Optionally:

__list(autostartActions)__: Actions that must be launched on plugin initialization
__int(priority)__: Sets the priority of the plugin
__dict({action:priority})__: Sets the priority of action

