#!/bin/bash

# Process and train a custom recording created with Spectacular Rec.
# Trains two versions: baseline and deblurred and renders a video that
# shows their differences. With normal, not-very-blurry recordings, the
# expected improvement is subtle but noticeable.

set -eu

NAME_W_EXT=`basename "$1"`
NAME=${NAME_W_EXT%.zip}

echo "============= Training motion-blur compensated model =========="
./scripts/process_and_train_sai_custom_mb.sh "$1"

echo "============= Training baseline model =========="
python train.py data/inputs-processed/custom/$NAME  \
    --no_eval --train_all --no_rolling_shutter --no_pose_opt --no_motion_blur --preview

echo "============= Rendering comparison video =========="
./scripts/render_and_compile_comparison_video.sh \
    "data/outputs/custom/train_all/$NAME" \
    "data/outputs/custom/motion_blur-train_all/$NAME"

echo "Success: see data/renders/$NAME-comparison.mp4"