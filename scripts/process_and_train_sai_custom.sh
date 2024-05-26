#!/bin/bash

# Process and train a custom recording created with Spectacular Rec.
#
# This version uses both motion blur compensation only and should work
# well with iPhone data and other devices with short rolling shutter
# readout times (or global shutter cameras)
#
# Run as
#
#   ./scripts/process_and_train_sai_custom.sh /PATH/TO/RECORDING.zip
#
# or, in headless mode
#
#   SAI_PREVIEW=OFF ./scripts/process_and_train_sai_custom.sh \
#       /PATH/TO/RECORDING.zip

set -eux

NAME_W_EXT=`basename "$1"`
NAME=${NAME_W_EXT%.zip}

: "${SAI_PREVIEW:=ON}"
: "${SKIP_COLMAP:=OFF}"
if [ $SAI_PREVIEW == "ON" ]; then
    PREVIEW_FLAG="--preview"
else
    PREVIEW_FLAG=""
fi
if [ $SKIP_COLMAP == "ON" ]; then
    COLMAP_FLAG="--skip_colmap"
else
    COLMAP_FLAG=""
fi

python process_sai_custom.py "$1" $COLMAP_FLAG $PREVIEW_FLAG
python train.py data/inputs-processed/custom/$NAME --no_eval --train_all $PREVIEW_FLAG