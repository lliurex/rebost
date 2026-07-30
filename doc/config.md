# Configuration

Rebost could be configured from its configuration file at /usr/share/rebost/rebost.conf

```
{
    "verifiedprovider": ["addon1","addon2"],
    "onlyverified":(true|false),
	"externalinstaller":"path/to/installer"
    "release":"data version"
}
```

The fields are:
- onlyverified: Bool, set the only verified flag that makes rebost show only verified or full catalogue
- verfiedprovider: Array, addons that are verified. All of the apps provided by them will be included. Apps from other addons only will be included if exists in verified
- externalInstaller: Rebost has no managing capabilities so it uses an external app for install/remove packages.
- release: The version of data. If rebost detects a mismatch between this and its own version of data will refresh all the info
