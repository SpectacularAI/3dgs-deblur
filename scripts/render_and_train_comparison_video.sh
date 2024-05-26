#!/bin/bash

# Process and train 3DGS from a video with and without deblurring
# (or rolling shutter compensation if ROLLINGS_SHUTTER=ON) and
# render a comparison video

set -eux

NAME_W_EXT=`basename "$1"`
NAME="${NAME_W_EXT%.*}"

: "${ROLLING_SHUTTER:=OFF}"

if [ $ROLLING_SHUTTER == "ON" ]; then
    MODE_NAME="rolling_shutter"
    export OURS_NAME="Compensated"
else
    MODE_NAME="motion_blur"
    export OURS_NAME="Deblurred"
fi
export ROLLING_SHUTTER

echo "============= Training $MODE_NAME compensated model =========="
./scripts/process_and_train_video.sh "$1"

echo "============= Training baseline model =========="
TARGET_DIR="data/inputs-processed/custom/$NAME"
python train.py "$TARGET_DIR" --no_rolling_shutter --no_pose_opt \
    --no_motion_blur --no_velocity_opt --train_all --no_eval

echo "============= Rendering comparison video =========="
./scripts/render_and_compile_comparison_video.sh \
    "data/outputs/custom/baseline/$NAME" \
    "data/outputs/custom/pose_opt-${MODE_NAME}-velocity_opt-zero_init/$NAME"

echo "Success: see data/renders/$NAME-comparison.mp4"