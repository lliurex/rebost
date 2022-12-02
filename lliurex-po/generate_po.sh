#!/bin/bash

PYTHON_FILES="../rebostGui/*.py ../rebostGui/stacks/*.py"

mkdir -p rebostGui

xgettext $UI_FILES $PYTHON_FILES -o rebostGui/rebostGui.pot


