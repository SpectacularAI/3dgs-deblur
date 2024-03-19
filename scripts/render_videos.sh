#!/bin/bash
set -eux

for case in iphone-pots2 iphone-lego1; do
    for variant in motion_blur baseline; do
        python render_video.py \
            data/outputs/colmap-sai-cli-vels-blur-scored/$variant/$case \
            --zoom=1.6 \
            --fps=24 \
            -o=data/renders/${case}_$variant.mp4
    done
done

python render_video.py \
    data/outputs/synthetic-posenoise-2nd-pass/baseline/cozyroom \
    --rolling_shutter_time=16 \
    --artificial_relative_look_at_distance=4 \
    --artificial_y_rounds=5 \
    --zoom=1.1 \
    --fps=24 \
    --video_crf=21 \
    -o=data/renders/synthetic_rolling_shutter_example.mp4

python render_video.py \
    data/outputs/synthetic-posenoise-2nd-pass/baseline/cozyroom \
    --exposure_time=8 \
    --artificial_relative_look_at_distance=4 \
    --artificial_y_rounds=5 \
    --zoom=1.1 \
    --fps=24 \
    --video_crf=21 \
    -o=data/renders/synthetic_motion_blur_example.mp4