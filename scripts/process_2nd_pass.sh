#!/bin/bash
set -eux

# Create all inputs for the pose optimization 2nd pass
# for dataset variants appearing in the paper

# Synthetic data
python combine.py \
    --dataset=synthetic-posenoise \
    --pose_opt_pass_dir data/outputs/synthetic-posenoise/pose_opt-train_all \
    all

# Real-data
python combine.py \
    --dataset=colmap-sai-cli-orig-intrinsics-blur-scored \
    --pose_opt_pass_dir data/outputs/colmap-sai-cli-orig-intrinsics-blur-scored/pose_opt-rolling_shutter-train_all/ \
    all

python combine.py \
    --dataset=colmap-sai-cli-calib-intrinsics-blur-scored \
    --pose_opt_pass_dir data/outputs/colmap-sai-cli-calib-intrinsics-blur-scored/pose_opt-rolling_shutter-train_all/ \
    all

python combine.py \
    --dataset=colmap-sai-cli-no-blur-select-orig-intrinsics \
    --pose_opt_pass_dir data/outputs/colmap-sai-cli-no-blur-select-orig-intrinsics/pose_opt-rolling_shutter-train_all/ \
    all