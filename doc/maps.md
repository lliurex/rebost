# Application mapping

Rebost fills its information from not-always-standard appstream catalogues.

The different addons generate appstream information from its own sources so sometimes could be errors identifying an application or same app could have many names across the sources. The mapping mechanism helps identifying this apps stablishing aliases between the provided names and the must-have names.
Also let declare hidden applications, as sometimes the sources of the addons don't let do this in an easy way.

## File location

The map files are located at /usr/share/rebost-data/lists.d/{release}/, where {release} is the codename of the current OS release.
On boot they're refreshed from internet, at github's rebost-data repository.

## File structure

They're pretty simple json files. The structure is:
```
    "upstream": "url" # The url of the map file. This url is unique for each map file.
    "nodisplay": 
		[
			"appId-1",
			"appId-2",
			...
		], #Array of appsId to hide
	"aliases":
		{
			"addonName": "mustBeName",
			,,,
		} #Dict of "invalidName":"goodName"
}
```

## Mechanism

On boot or when a reload is requested Rebost reads the local map files and update them from the "upstream" url of each one.
The resulting file is stored in rebost cache at /var/cache/rebost for future readings.

After the map files are processed rebost begins to parse the different addons catalogues. If an appId is find in "nodisplay" then is discarded, if is in the "aliases" section then the appId is changed to the aliased and the old name is stored as tag for searches.

