#!/bin/bash

GUI_FILES="../rebostGui/*.py ../rebostGui/stacks/*.py"
CLI_FILES="../rebost/rebostCli.py"

mkdir -p rebostGui
mkdir -p rebost

xgettext $GUI_FILES -o rebostGui/rebostGui.pot
xgettext $CLI_FILES -o rebost/rebost.pot


