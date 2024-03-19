#!/bin/bash

# Package the code in this repository (excluding VIO into a zip)
DATE=$(date +%Y-%m-%dT%H-%M)
code_zip="data/code_$DATE.zip"
data_zip="data/data_$DATE.zip"

# Package the current directory, excluding .git directories and specified folders
zip -r "$code_zip" .\
  -x 'venv/*' \
  -x 'gsplat/build/*' \
  -x '*.so' \
  -x '*.o' \
  -x '*.git*' \
  -x 'data/*' \
  -x 'vio/*' \
  -x '*__pycache__*' \
  -x '*egg-info*'

echo "Packaged: $code_zip"
