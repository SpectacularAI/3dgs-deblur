#!/bin/bash
set -eux

SRC_FOLDER="source_videos"
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
done

for CASE in s20-sign s20-bike; do
    ffmpeg \
        -i "$SRC_FOLDER/$CASE.mp4" \
        -vf "scale=768x512" \
        -c:v libx264 -crf 22 -qp 0 -y -pix_fmt yuv420p \
        -to 16 \
        "static/videos/$CASE.mp4"
done
