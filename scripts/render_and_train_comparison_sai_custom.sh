#!/bin/bash

# Process and train a custom recording created with Spectacular Rec.
# Trains two versions: baseline and deblurred and renders a video that
# shows their differences. With normal, not-very-blurry recordings, the
# expected improvement is subtle but noticeable.

set -eu

NAME_W_EXT=`basename "$1"`
NAME=${NAME_W_EXT%.zip}

echo "============= Training motion-blur compensated model =========="
# Note: do not set SKIP_COLMAP here: the 3DGS reconstruction may work
# fine but the comparison video will often be misaligned
./scripts/process_and_train_sai_custom.sh "$1"

echo "============= Training baseline model =========="
python train.py data/inputs-processed/custom/$NAME  \
    --no_eval --train_all --no_rolling_shutter --no_pose_opt --no_motion_blur --no_velocity_opt --preview

echo "============= Rendering comparison video =========="
./scripts/render_and_compile_comparison_video.sh \
    "data/outputs/custom/baseline/$NAME" \
    "data/outputs/custom/pose_opt-motion_blur-rolling_shutter-velocity_opt/$NAME"

echo "Success: see data/renders/$NAME-comparison.mp4"