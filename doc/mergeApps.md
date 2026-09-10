# App merging in Rebost

Each add-on provides Rebost with an appstream catalogue of included applications. Rebost then merges all this catalogues into its main catalogue.
The merge of apps is an intricated system based on heuristics, aliases (as seen in [maps.md] map files) and assumptions of what is really what because not all the add-ons give accurate info and not all of them use the same identifiers for apps.

## Collecting data, trusted or not

After collecting all data from addons Rebosts executes a number of steps:

1 Addons are sorted in two lists. One for verified sources (see [configuration](config.md)) and other for non-verified

2 If "verified_only" is enabled the verified sources are processed
  - For each app rebost searches in its verified catalogue. If app is found then the info of new and existent is merged
  - the app is added to the generic catalogue

3 Non-verified addons are processed sequentially.
	- For each app rebost searches in the verified catalogue. If exists then app is mered, if is unexsitent then is discarded
	- The app is then searched in generic catalogue and merged or added if exists or not

## Merge process

When rebost tries to add a app that exists it throws a mergin mechanism for adding new provided overwriting the existing one. This process is based on [appstreamglib.App.subsume and appstreamglib.App.subsume_full](https://lazka.github.io/pgi-docs/#AppStreamGlib-1.0/classes/App.html#AppStreamGlib.App.subsume) and honours the existing data.
In that manner as verified sources are processed first their data is preserved and only new and non-existent info is added to it.

Flow of app merge:

1 Rebost reads app from catalogue
2 If there's a match
  1 Merge old info with new
  2 Remove old info
  3 Update app
3 Insert app 

## Verified and generic catalogues

As seen rebost uses two different catalogues. Verified catalogue contains only apps from verified sources, Generic contains all processed apps. Both catalogues are in appstream format and could be exported. Rebost could switch between them givin' an on demand access to all or only verified applications.
