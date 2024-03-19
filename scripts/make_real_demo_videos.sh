#!/bin/bash
set -eux

SRC_FOLDER="source_videos"
OUT_FOLDER="static/videos"

mkdir -p "$OUT_FOLDER"
cp -f "$SRC_FOLDER"/*.mp4 "$OUT_FOLDER"

for CASE in iphone-pots2 iphone-lego1; do
    OUT_FILE="$OUT_FOLDER/real-$CASE.mp4"
    SCALE="800x600" \
    OVERLAY_BASE=overlay_images/overlay_800x600_splatfacto.png \
    OVERLAY_OURS=overlay_images/overlay_800x600_deblurred.png ./scripts/combine_videos.sh \
        "$SRC_FOLDER/${CASE}_baseline.mp4" \
        "$SRC_FOLDER/${CASE}_motion_blur.mp4" \
        "$OUT_FILE"
done