#!/bin/bash

# Process and train a custom recording created with Spectacular Rec.
#
# This version uses both motion blur, rolling shutter compensation in a
# two-pass process: first pass optimizes poses with rolling shutter
# compensation enabled, second pass trains 3DGS with rolling shutter and
# motion blur compensation enabled and fixed poses.
#
# This mode is intended for Android recordings with long rolling shutter
# readout times.
#
# Run as
#
#   ./scripts/process_and_train_sai_custom_mbrs_pose_opt.sh \
#       /PATH/TO/RECORDING.zip
#
# or, in headless mode
#
#   SAI_PREVIEW=OFF ./scripts/process_and_train_sai_custom_mbrs_pose_opt.sh \
#       /PATH/TO/RECORDING.zip
#
# Optionally, COLMAP can be skipped entirely. Then Spectacular AI poses
# will be used as starting point. This can help with very difficult cases
# where COLMAP fails or can be used to speed up processing, by skipping an
# unnecessary step:
#
#   SKIP_COLMAP=ON ./scripts/process_and_train_sai_custom_mbrs_pose_opt.sh \
#       /PATH/TO/RECORDING.zip
#

set -eux

NAME_W_EXT=`basename "$1"`
NAME=${NAME_W_EXT%.zip}

: "${SAI_PREVIEW:=ON}"
if [ $SAI_PREVIEW == "ON" ]; then
    PREVIEW_FLAG="--preview"
else
    PREVIEW_FLAG=""
fi

: "${SKIP_COLMAP:=OFF}"
if [ $SKIP_COLMAP == "ON" ]; then
    python process_sai_custom.py "$1" --skip_colmap $PREVIEW_FLAG
else
    python process_sai_custom.py "$1" --keep_intrinsics $PREVIEW_FLAG
fi

echo "------------- 1st pass: rolling-shutter aware pose optimization ---------------"
rm -rf data/outputs/custom/pose_opt-rolling_shutter-train_all/$NAME
python train.py data/inputs-processed/custom/$NAME --train_all --no_motion_blur

echo "------------- 2nd pass: motion-blur compensated 3DGS ---------------"
python combine.py \
    data/outputs/custom/pose_opt-rolling_shutter-train_all/$NAME \
    data/inputs-processed/custom/$NAME \
    data/inputs-processed/custom-2nd-pass/$NAME \
    --pose_opt_pass_dir=data/outputs/custom/pose_opt-rolling_shutter-train_all 

python train.py data/inputs-processed/custom-2nd-pass/$NAME --no_eval --train_all --no_pose_opt --preview