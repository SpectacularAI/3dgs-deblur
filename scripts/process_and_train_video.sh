#!/bin/bash

# Process and train deblurred 3DGS from a video.
# set ROLLING_SHUTTER=ON to train a rolling shutter compensated model instead
# of a deblurred one. For simultaneous MB and RS compensation, see
# process_and_train_sai_custom.sh

set -eux

NAME_W_EXT=`basename "$1"`
NAME="${NAME_W_EXT%.*}"

: "${ROLLING_SHUTTER:=OFF}"

: "${PREVIEW:=ON}"
if [ $PREVIEW == "ON" ]; then
    PREVIEW_FLAG="--preview"
else
    PREVIEW_FLAG=""
fi

if [ $ROLLING_SHUTTER == "ON" ]; then
    MODE_FLAGS="--no_motion_blur"
else
    MODE_FLAGS="--no_rolling_shutter"
fi

mkdir -p "data/inputs-processed/custom"
TARGET_DIR="data/inputs-processed/custom/$NAME"

ns-process-data video --num-frames-target 100 --data "$1" --output-dir "$TARGET_DIR"
python train.py "$TARGET_DIR" $MODE_FLAGS --velocity_opt_zero_init --train_all --no_eval $PREVIEW_FLAG