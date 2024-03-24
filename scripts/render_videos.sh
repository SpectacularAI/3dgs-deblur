#!/bin/bash
# Render raw material for the demo videos
# Assumes you have ran "train.py" with all of the synthetic
# cases (including 2nd pass) and most of the smartphone datasets

set -eux

for case in factory cozyroom tanabata pool; do
    reso="960x640"
    zoom=1.05
    python render_video.py \
        data/outputs/synthetic-mb/baseline/${case} \
        --video_crf=21 \
        --resolution=${reso} \
        --zoom=${zoom} \
        --fps=60 \
        -o=data/renders/synthetic-${case}-mb-baseline-${reso}.mp4

    python render_video.py \
        data/outputs/synthetic-mb/motion_blur/${case} \
        --video_crf=21 \
        --resolution=${reso} \
        --zoom=${zoom} \
        --fps=60 \
        -o=data/renders/synthetic-${case}-mb-ours-${reso}.mp4

    python render_video.py \
        data/outputs/synthetic-rs/baseline/${case} \
        --video_crf=21 \
        --resolution=${reso} \
        --zoom=${zoom} \
        --fps=60 \
        -o=data/renders/synthetic-${case}-rs-baseline-${reso}.mp4
        
    python render_video.py \
        data/outputs/synthetic-rs/rolling_shutter/${case} \
        --video_crf=21 \
        --resolution=${reso} \
        --zoom=${zoom} \
        --fps=60 \
        -o=data/renders/synthetic-${case}-rs-ours-${reso}.mp4

    python render_video.py \
        data/outputs/synthetic-posenoise/baseline/${case} \
        --video_crf=21 \
        --resolution=${reso} \
        --zoom=${zoom} \
        --fps=60 \
        -o=data/renders/synthetic-${case}-posenoise-baseline-${reso}.mp4
        
    python render_video.py \
        data/outputs/synthetic-posenoise-2nd-pass/baseline/${case} \
        --video_crf=21 \
        --resolution=${reso} \
        --zoom=${zoom} \
        --fps=60 \
        -o=data/renders/synthetic-${case}-posenoise-ours-${reso}.mp4
done

python render_video.py \
    data/outputs/colmap-sai-cli-vels-blur-scored/motion_blur/iphone-pots2 \
    --zoom=1.6 \
    --fps=60 \
    --rolling_shutter_time=15 \
    --artificial_relative_look_at_distance=1.75 \
    --artificial_y_rounds=3 \
    --artificial_relative_motion_scale=0.2 \
    --artificial_length_seconds=4 \
    -o=data/renders/synthetic_rolling_shutter_from_real_data.mp4

python render_video.py \
    data/outputs/colmap-sai-cli-vels-blur-scored/motion_blur/iphone-pots2 \
    --zoom=1.6 \
    --fps=24 \
    --exposure_time=8 \
    --artificial_relative_look_at_distance=1.75 \
    --artificial_y_rounds=1 \
    --artificial_relative_motion_scale=0.2 \
    --artificial_length_seconds=4 \
    -o=data/renders/synthetic_motion_blur_from_real_data.mp4

python render_video.py \
    data/outputs/synthetic-posenoise-2nd-pass/baseline/cozyroom \
    --rolling_shutter_time=40 \
    --artificial_relative_look_at_distance=4 \
    --artificial_y_rounds=5 \
    --zoom=1.1 \
    --fps=60 \
    --resolution=960x640 \
    --video_crf=21 \
    -o=data/renders/synthetic_rolling_shutter_example_960x640.mp4

python render_video.py \
    data/outputs/synthetic-posenoise-2nd-pass/baseline/cozyroom \
    --exposure_time=20 \
    --artificial_relative_look_at_distance=4 \
    --artificial_y_rounds=5 \
    --zoom=1.1 \
    --resolution=960x640 \
    --fps=60 \
    --video_crf=21 \
    -o=data/renders/synthetic_motion_blur_example_960x640.mp4
    

python render_video.py \
    data/outputs/colmap-sai-cli-vels-blur-scored/motion_blur/iphone-pots2 \
    --zoom=1.6 \
    --fps=60 \
    --exposure_time=1 \
    --rolling_shutter_time=4 \
    --artificial_relative_look_at_distance=1.5 \
    --artificial_y_rounds=1 \
    --artificial_relative_motion_scale=1 \
    --artificial_length_seconds=1 \
    --artificial_keep_center_pose \
    -o=data/renders/synthetic_mbrs_from_real_data_keep.mp4

python render_video.py \
    data/outputs/colmap-sai-cli-vels-blur-scored/motion_blur/iphone-pots2 \
    --zoom=1.6 \
    --fps=60 \
    --rolling_shutter_time=4 \
    --artificial_relative_look_at_distance=1.5 \
    --artificial_y_rounds=1 \
    --artificial_relative_motion_scale=1 \
    --artificial_length_seconds=1 \
    --artificial_keep_center_pose \
    -o=data/renders/synthetic_rolling_shutter_from_real_data_keep.mp4

python render_video.py \
    data/outputs/colmap-sai-cli-vels-blur-scored/motion_blur/iphone-pots2 \
    --zoom=1.6 \
    --fps=24 \
    --exposure_time=1 \
    --artificial_relative_look_at_distance=1.5 \
    --artificial_y_rounds=2 \
    --artificial_relative_motion_scale=1 \
    --artificial_length_seconds=3 \
    --artificial_keep_center_pose \
    -o=data/renders/synthetic_motion_blur_from_real_data_keep.mp4


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