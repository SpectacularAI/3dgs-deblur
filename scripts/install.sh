#!/bin/bash
set -eux

: "${BUILD_NERFSTUDIO:=ON}"
: "${INSTALL_SAI:=ON}"

# You may also need to run this
# pip install --upgrade pip setuptools

if [ $BUILD_NERFSTUDIO == "ON" ]; then
    # Install the custom fork of Nerfstudio
    cd nerfstudio
    pip install -e .
    cd ..
fi

# ... then install the custom gsplat (order may matter here!)
if [ $BUILD_NERFSTUDIO == "ON" ]; then
    cd gsplat
    pip install -e .
    cd ..
fi

if [ $INSTALL_SAI == "ON" ]; then
    pip install spectacularAI[full]==1.31.0
fi