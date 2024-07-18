#!/bin/bash

GUI_FILES="../rebostGui/*.py ../rebostGui/stacks/*.py"
CLI_FILES="../rebost/rebostCli.py"

mkdir -p rebostGui
mkdir -p rebost

xgettext $GUI_FILES -o rebostGui/rebostGui.pot
xgettext $CLI_FILES -o rebost/rebost.pot

#Categories
CAT=$(qdbus net.lliurex.rebost /net/lliurex/rebost net.lliurex.rebost.getCategories)
if [[ $? -eq 0 ]]
then
	CAT=${CAT/[/}
	CAT=${CAT/]/}
	CAT=${CAT//,/}
	#CAT=($CAT)
	echo "" >> rebostGui/rebostGui.pot
	IFS=$'\"'
	for i in ${CAT}
	do
		if [[ x${i// /} != "x" ]]
		then
			echo "msgid \"${i//_/}\"" >> rebostGui/rebostGui.pot
			echo "msgstr \"\"" >> rebostGui/rebostGui.pot
			echo "" >> rebostGui/rebostGui.pot
		fi
	done
fi


