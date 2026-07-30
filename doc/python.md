# Python module

```
from rebost import store

client=store.client()
client.getApps()
```

As simple as import the module and use it.

## Methods
* getConfig
	* Input: None
	* Return: { key:value } Dict of config options

* getSupportedFormats
	* Input: None
	* Return: [ str ] Array of supported formats

* getFreedesktopCategories
	* Input: None
	* Return: { category:[ subcategories ] } Dict of categories with subcategories as suggested by freedesktop

* export
	* Input: Destination file (str) Path to file
	* Return: None
 Export applications to destination file

* searchApp
	* Input: Search string (str)
	* Return: { score:application }
   
 Search applications by string. The search results are ordered by match score. searchApp includes results by name, description, keywords...

* searchAppByUrl
	* Input: Searched url (str)
	* Return: application
   
 Search by matching url. The url is taken from the application's homepage

* showApp
	* Input: Application name (str)
	* Return: Application
   
 Returns the application data related to the given name

* refreshApp
	* Input: Application name (str)
	* Return: Application
   
 Return the application after refreshing the cache data

* getCategories
	* Input: None
	* Return: [ categories ] Array of categories
   
 Not used. The different package or bundle systems don't ever use standarized categories. This method returns all the categories collected

* getApps
	* Input: None
	* Return: [ applications ] Array of applications
   
 Returns all the applications in rebost

* getAppsPerCategory
	* Input: None
	* Return: { category: [ applications ] } A dict of applications ordered by category

* getAppsInstalled
	* Input: None
	* Return: [ applications ] Array of installed applications

* setStateForApp
	* Input: Application id, state, bundle (optional), temp (optional)
	* Output: None
   
 Set application's state as indicated, optionally only for a specified bundle or temporally.
 The state is one of appstreamglib.AppState. If temporally is not indicated or is true (true/false) the state is stored, otherwise only is setted after next data reload

* getExternalInstaller
	* Input: None
	* Output: Path to an application's installer
   
 Rebost itself doesn't do operations with applications but an external application could be configured. This method returns the path of that applications, in LliureX is the Epi Manager.

# Examples

* Listing installed apps from python

```
#!/usr/bin/env python3
from rebost import store
import json

client=store.client()
installedApps=client.getAppsInstalled()
for app in json.loads(installedApps):
	print(app["id"])
```
