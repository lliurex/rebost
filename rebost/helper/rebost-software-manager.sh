#!/bin/bash
#License GPL-3
#Copyright 2021 LliureX Team
#Parms: $1 -> package; $2 -> cli/gui mode
/usr/sbin/epi-gtk -nc -d $1 > /tmp/rebost/epigtk.log
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
