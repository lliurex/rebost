#!/bin/bash
#License GPL-3
#Copyright 2021 LliureX Team
#Parms: $1 -> package; $2 -> cli/gui mode
if [[ $2 == "cli" ]]
then
	/usr/sbin/epic $3 -nc -d $1 > /tmp/rebost/epigtk.$USER.log
else
	/usr/sbin/epi-gtk -nc -u $1 $3 > /tmp/rebost/epigtk.$USER.log
fi

TMPDIR=$(dirname $1)
#Check if what is told to remove is also what we want to remove
####if [ -e $1 ]
####then
####	if [[ ${TMPDIR:0:8} == "/tmp/tmp" ]]
####	then
####		if [[ ${1/*./.} == ".epi" ]]
####		then 
####			rm -r $TMPDIR
####		fi
####	fi
####fi
