#!/bin/bash
set -eux

INPUT_BASE="$1"
INPUT_OURS="$2"

# zoom 2x original focal length to highlight details, slow speed (approx.)
RENDER_ARGS="--zoom=1.5 --original_trajectory --playback_speed=0.25"

NAME=`basename "$INPUT_BASE"`

mkdir -p data/renders

BASE_VID="data/renders/$NAME-baseline.mp4"
OURS_VID="data/renders/$NAME-deblurred.mp4"
COMP_VID="data/renders/$NAME-comparison.mp4"

python render_video.py $RENDER_ARGS "$INPUT_BASE" -o "$BASE_VID"
python render_video.py $RENDER_ARGS "$INPUT_OURS" -o "$OURS_VID"

./scripts/compile_comparison_video.sh "$BASE_VID" "$OURS_VID" "$COMP_VID"