# README

Rebost is a software querying system for Lliurex (and probably others) distribution. 
It has a plugin mechanism for supporting almost any package manager or bundle distribution format out in the wild. Among the included plugins at least there're plugins for Slackware's slackpkg and limba bundles demonstrating the flexibility of the plugin mechanism.

# Usage

Rebost, as specified, isn't a software management per se. Its main purpose is to collect the information from the different plugins and offer it to software stores through appstream or in its own json based format. The information could be accessed through a python module or d-bus giving the stores the freedom and need to implement the management tasks (install/uninstall basically).

# Configuration

Rebost main configuration is stored at /usr/share/rebost/rebost.conf in json format.
The following keys are supported:
```
{
    "verifiedProvider": ['origins'], Array of verified origins as specified by plugins
    "onlyVerified":true/false, Load only applications included in verified providers. If an application isn't included in a verified provided is excluded from rebost. If exists then the data gets collected from all plugins
	"externalInstaller": installer's path. Path to an installer
    "release": Data release number. Release of the data format. If rebost detects a mismatch between data release and it's own data format the cache would be regenerated.
}
```
# Documentation

Docs with API and examples are located at [docs](doc)


