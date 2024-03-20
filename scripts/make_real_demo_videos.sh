#!/bin/bash
set -eux

SRC_FOLDER="data/renders"
OUT_FOLDER="static/videos"

mkdir -p "$OUT_FOLDER"
cp -f "$SRC_FOLDER"/synthetic_*_example.mp4 "$OUT_FOLDER"

for CASE in iphone-pots2 iphone-lego1; do
    OUT_FILE="$OUT_FOLDER/real-$CASE.mp4"
    SCALE="800x600" \
    OVERLAY_BASE=overlay_images/overlay_800x600_splatfacto.png \
    OVERLAY_OURS=overlay_images/overlay_800x600_deblurred.png ./scripts/combine_videos.sh \
        "$SRC_FOLDER/${CASE}_baseline.mp4" \
        "$SRC_FOLDER/${CASE}_motion_blur.mp4" \
        "$OUT_FILE"

    OUT_FILE="data/renders/real-$CASE-1920x1280.mp4"
    SCALE="1920x1280" \
    OVERLAY_BASE=overlay_images/overlay_1920x1280_splatfacto.png \
    OVERLAY_OURS=overlay_images/overlay_1920x1280_deblurred.png ./scripts/combine_videos.sh \
        "$SRC_FOLDER/${CASE}_baseline.mp4" \
        "$SRC_FOLDER/${CASE}_motion_blur.mp4" \
        "$OUT_FILE"
done

for CASE in s20-sign s20-bike; do
    ffmpeg \
        -i "$SRC_FOLDER/$CASE.mp4" \
        -vf "scale=768x512" \
        -c:v libx264 -crf 22 -qp 0 -y -pix_fmt yuv420p \
        -to 16 \
        "static/videos/$CASE.mp4"
done

for CASE in iphone-pots2 iphone-lego1; do
    OUT_FILE="data/renders/$CASE-long.mp4"
    RENDERS_FOLDER="$SRC_FOLDER/colmap-sai-cli-vels-blur-scored"
    ORIG_FOLDER="data/inputs-raw/spectacular-rec"
    ./scripts/combine_real_videos.sh \
        "$RENDERS_FOLDER/baseline/$CASE/demo_video.mp4" \
        "$RENDERS_FOLDER/motion_blur/$CASE/demo_video.mp4" \
        "$ORIG_FOLDER/$CASE/data.mov" \
        "$OUT_FILE"
done