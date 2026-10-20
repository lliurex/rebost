# README

Rebost is a software querying system for Lliurex (and probably others) distribution. 
It has a plugin mechanism for supporting almost any package manager or bundle distribution format out in the wild. Among the included plugins at least there're plugins for Slackware's slackpkg and limba bundles demonstrating the flexibility of the plugin mechanism.

# Usage

Rebost, as specified, isn't a software management per se. Its main purpose is to collect the information from the different plugins and offer it to software stores in [appstream metadata](https://www.freedesktop.org/software/appstream/docs/chap-AppStream-About.html) or in [its own json based format](doc/pkgFormat.md). The information could be accessed from a python module or d-bus queries, giving the stores the freedom and need to implement the management tasks (install/uninstall basically).

# Documentation

Docs with API and examples are located at [docs](doc)


