#!/bin/bash
set -eux

SRC_FOLDER="data/renders"
OUT_FOLDER="static/videos"

mkdir -p "$OUT_FOLDER"
cp "$SRC_FOLDER"/synthetic_*_example.mp4 "$OUT_FOLDER"

for f in $SRC_FOLDER/synthetic-posenoise/baseline/*; do
    CASE=$(basename $f)
    OUT_FILE="$OUT_FOLDER/posenoise-$CASE.mp4"

    OVERLAY_OURS=overlay_images/overlay_600x400_optimized.png ./scripts/combine_videos.sh \
        "$SRC_FOLDER/synthetic-posenoise/baseline/$CASE/demo_video.mp4" \
        "$SRC_FOLDER/synthetic-posenoise-2nd-pass/baseline/$CASE/demo_video.mp4" \
        "$OUT_FILE"
done

RENDERS_FOLDER="$SRC_FOLDER/synthetic-rs"

for f in $RENDERS_FOLDER/baseline/*; do
    CASE=$(basename $f)
    OUT_FILE="$OUT_FOLDER/rs-$CASE.mp4"

    OVERLAY_OURS=overlay_images/overlay_600x400_compensated.png ./scripts/combine_videos.sh \
        "$RENDERS_FOLDER/baseline/$CASE/demo_video.mp4" \
        "$RENDERS_FOLDER/rolling_shutter/$CASE/demo_video.mp4" \
        "$OUT_FILE"
done

RENDERS_FOLDER="$SRC_FOLDER/synthetic-mb"

for f in $RENDERS_FOLDER/baseline/*; do
    CASE=$(basename $f)
    OUT_FILE="$OUT_FOLDER/mb-$CASE.mp4"

    ./scripts/combine_videos.sh \
        "$RENDERS_FOLDER/baseline/$CASE/demo_video.mp4" \
        "$RENDERS_FOLDER/motion_blur/$CASE/demo_video.mp4" \
        "$OUT_FILE"
done