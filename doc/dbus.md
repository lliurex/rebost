# D-Bus methods

Rebost stablishes a system d-bus service at _net.lliurex.rebost_ under the path _/net/lliurex/rebost_.
The available methods returns a stringfied array of dictionaries containing information in rebost own package format.

## Public accessible methods

This methods are accessible by any user and are related with basic functionality and application queries.

- export [string path]: Generates a valid appstream xml at given path, /tmp by default, with all the applications
- getConfig: Returns an stringfied dict with the configuration
- getMaps: Returns an stringfied dict with the [application mapping](maps.md)
- getFreeDesktopCategories: Returns an stringfied array of hashes with standard categories and their subcategories
- getApps: Returns an stringfied array of dictionaries in [rebost format](pkgFormat.md) with all the included apps
- getAppsInCategory [string category]: As getApps but for only apps in given category
- getAppsInstalled: As getapps but only installed apps
- getAppsInstalledPerCategory: Returns an array of summarized apps installed per category 
- search [string query]: Searches for given string and returns an stringfied array of dictionaries with the results
- showApp [string appId]: Returns a stringfied dictionary of appId in rebost format
- refreshApp [string appId]: Forces a data refresh for appId and returns an stringfied dictionary of it
- searchAppByUrl [string url]: Returns an array of rebost packages containing apps with given url in its home or info pages

## Restricted methods

This methods are only available for users with permissions

- toggleLock: Changes between the restricted and unrestricted store
- getExternalInstaller: Returns the external installer to use as specified in config
- setAppState [string appId, int state, string bundle]: Sets the specified bundle to given state in appId
- setAppStateTmp [string appId, int state, string bundle]: As before but only till rebost restart
- restart: Forces rebost to reload all data
- rawApp [string appId]: Returns the raw data of and application

# Examples
```
$ qdbus --system net.lliurex.rebost /net/lliurex/rebost net.lliurex.rebost.showApp alea
```
> [{"bundle": {"unknown": "zero-installer-util-classroom.epi", "package": "alea"}, "versions": {"package": "0.23.2"}, "status": {"package": 1}, "id": "alea", "name": "Alea", "description": "Autoritzada - Botiga", "summary": "Autoritzada - Botiga", "pkgname": "alea", "icon": "/usr/share/zero-installer-util-classroom/alea.png", "homepage": "https://portal.edu.gva.es/appsedu/alea/", "infopage": "", "state": 2, "suggests": [], "keywords": ["Utility", "alea", "appsedu", "classroom", "installer", "util", "zero", "zero-installer-util-classroom", "zero-installer-util-classroom.epi"], "origin": null, "categories": ["Utility"], "license": null, "screenshots": []}]
