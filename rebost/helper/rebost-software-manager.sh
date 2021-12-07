#!/bin/bash
#License GPL-3
#Copyright 2021 LliureX Team
/usr/sbin/epi-gtk -nc $1
tmpDir=$(dirname $1)
if [[ tmpDir":x" != ":x" ]]
then
	rm -r $tmpDir
fi
