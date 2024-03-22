#!/bin/bash

# Process and train a custom recording created with Spectacular Rec.
#
# This version uses both motion blur compensation only and should work
# well with iPhone data and other devices with short rolling shutter
# readout times (or global shutter cameras)
#
# Run as
#
#   ./scripts/process_and_train_sai_custom_mb.sh /PATH/TO/RECORDING.zip
#
# or, in headless mode
#
#   SAI_PREVIEW=OFF ./scripts/process_and_train_sai_custom_mb.sh \
#       /PATH/TO/RECORDING.zip

set -eux

NAME_W_EXT=`basename "$1"`
NAME=${NAME_W_EXT%.zip}

: "${SAI_PREVIEW:=ON}"
if [ $SAI_PREVIEW == "ON" ]; then
    PREVIEW_FLAG="--preview"
else
    PREVIEW_FLAG=""
fi

python process_sai_custom.py "$1" $PREVIEW_FLAG
python train.py data/inputs-processed/custom/$NAME  --no_eval --train_all --no_rolling_shutter --no_pose_opt --preview