# ISSUES

As rebost is a meta crawler for different catalogues and not all of them are appstream compliant there're known issues that are hardly fixable.

## App status

When getting the status of an app there're a number of possible issues:

- Bundles of kind "unknown": An addon could provide "unknown" bundles (ie addon for Lliurex's epic) without a standarized way of get the status
- Aliased applications: A application that uses a alias could be missmatched if the alias only affectes one of the knowed bundles. IE an application distributed as package with name "app" and as flatpak with name "flatpakApp" aliased as "myApp". Thing could get even worse if there's also an unknown bundle
- Unknown bundles that are always marked as installed because they don't provide any package and are virtual or meta packages and with appId equal to main appId

## App upgrades

- Appimages has not standarized way of getting installed or available versions of an app.
- Snaps are auto upgraded
- If an addon doesn't provide release info then is impossible to know if there're available upgrades
