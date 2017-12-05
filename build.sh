#!/usr/bin/env bash
PROJECT_DIR=$(pwd)
PACKAGE_FILE=${PROJECT_DIR}/build/package.zip

rm -r build
mkdir build

virtualenv -p python3 .venv
source .venv/bin/activate
pip install -r requirements.txt

cd .venv/lib/python3.6/site-packages
zip -r9 ${PACKAGE_FILE} * -x "pkg_resources*" -x "setuptool*" -x "wheel*" -x "pip*" -x "*__pycache__*" -x "easy_install.py"
cd ${PROJECT_DIR}/src
zip -g ${PACKAGE_FILE} *.py

cd ${PROJECT_DIR}
deactivate