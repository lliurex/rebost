# Rebost package format

Although internally the info is stored in [Appstream metadata format](https://www.freedesktop.org/software/appstream/docs/chap-AppStream-About.html) externally is presented in rebost own json based format. This way the data returned by dbus or python-api is in the same format and the non-standard fields needed by LliureX could be implemented without breaking compatibility with appstream standard.

## Fields

A package in rebost has the next fields:

- "bundle" # The bundles this apps is distributed from. Each kind has the install candidate (be it a pkgname, flatpak id, url for dowlonad, etc..) as value.
  - "package":"pkgName"  
  - "appimage":"downloadUrl"
  - "flatpak": "flatpakId"
  - "snap": "snapName"
  - "unknown": "whatever"
- "versions": # For each bundle stores the version provided for the application
- "status": # For each bundle stores the status. 0 for installed, 1 for uninstalled. More on this at [status issues](issues.md)
- "id" # The appId, must be unique
- "name" # Name of the app in pretty format (ie: Gimp Photo Editor)
- "pkgname" # Deprecated,
- "icon" # Uri of the icon, remote or local
- "description" # Well... 
- "summary" # short description
- "homepage" # homepage of the application/project
- "infopage" # related webpage. Could be help-related, wiki, etc..
- "state" # the state of the app. Deprecated
- "suggests" # Array of suggested or related apps
- "keywords" # Array of tags for searching
- "origin" # Stores the origin of the app. Actually it only contains if is verified or not
- "categories" # Array of standard freedesktop categories the app belongs to
- "license" # App license
- "screenshots" # Array with urls of screenshots

# Appstream non-standard extensions

As rebost abuses of cached information the standard appstream has been expanded through metadata keys, so the produced info continues to be valid appstream metainfo.
The extended keys are:

- "X-REBOST-{bundle}": Stores status of the bundle

