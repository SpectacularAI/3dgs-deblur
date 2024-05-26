#!/bin/bash
# Render raw material for the demo videos
# Assumes you have ran "train.py" with all of the synthetic
# and most of the smartphone datasets

set -eux

: "${RENDER_SYNTHETIC:=ON}"
: "${RENDER_SMARTPHONE:=ON}"

fps=30

if [ $RENDER_SYNTHETIC == "ON" ]; then
    for reso in 640x400 1920x1080 960x640; do
        for case in factory cozyroom tanabata pool; do
            zoom=1.05
            python render_video.py \
                data/outputs/synthetic-mb/baseline/${case} \
                --resolution=${reso} \
                --zoom=${zoom} \
                --fps=$fps \
                -o=data/renders/synthetic-${case}-mb-baseline-${reso}.mp4

            python render_video.py \
                data/outputs/synthetic-mb/motion_blur/${case} \
                --resolution=${reso} \
                --zoom=${zoom} \
                --fps=$fps \
                -o=data/renders/synthetic-${case}-mb-ours-${reso}.mp4

            python render_video.py \
                data/outputs/synthetic-rs/baseline/${case} \
                --resolution=${reso} \
                --zoom=${zoom} \
                --fps=$fps \
                -o=data/renders/synthetic-${case}-rs-baseline-${reso}.mp4

            python render_video.py \
                data/outputs/synthetic-rs/rolling_shutter/${case} \
                --resolution=${reso} \
                --zoom=${zoom} \
                --fps=$fps \
                -o=data/renders/synthetic-${case}-rs-ours-${reso}.mp4

            python render_video.py \
                data/outputs/synthetic-posenoise/baseline/${case} \
                --resolution=${reso} \
                --zoom=${zoom} \
                --fps=$fps \
                -o=data/renders/synthetic-${case}-posenoise-baseline-${reso}.mp4

            python render_video.py \
                data/outputs/synthetic-posenoise/pose_opt/${case} \
                --resolution=${reso} \
                --zoom=${zoom} \
                --fps=$fps \
                -o=data/renders/synthetic-${case}-posenoise-ours-${reso}.mp4
        done
    done
fi

if [ $RENDER_SMARTPHONE == "ON" ]; then
    best_variant="pose_opt-motion_blur-rolling_shutter"
    for variant in $best_variant baseline; do
        for case in s20-sign s20-bike pixel5-lamp; do
            python render_video.py \
                data/outputs/colmap-sai-cli-vels-blur-scored/$variant/$case \
                --zoom=1.2 \
                --fps=$fps \
                --original_trajectory \
                --resolution=1080x960 \
                -o=data/renders/${case}_$variant.mp4
        done

        for case in pixel5-table iphone-pots2 iphone-lego1; do
            python render_video.py \
                data/outputs/colmap-sai-cli-vels-blur-scored/$variant/$case \
                --zoom=1.6 \
                --resolution=1920x1080 \
                --fps=$fps \
                -o=data/renders/${case}_$variant.mp4
        done
    done
fi