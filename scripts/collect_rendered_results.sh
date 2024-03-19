#!/bin/bash

# Helper script for collecting the images and videos scattered around
# data/outputs into a simpler directory structur data/renders

set -eu

: "${INPUT_FOLDER:=data/outputs}"
: "${OUTPUT_ROOT:=data/renders}"
: "${DO_CLEAR:=ON}"

if [ "$DO_CLEAR" = "ON" ]; then
    rm -rf "$OUTPUT_ROOT"
fi

find "$INPUT_FOLDER" -mindepth 1 -type f | grep "splatfacto" | grep "metrics.json" | while read f; do
    DIR=${f%/metrics.json}

    # keepin' it simple
    SESSION=$(basename $(dirname $(dirname $DIR)))
    VARIANT=$(basename $(dirname $(dirname $(dirname $DIR))))
    DATASET=$(basename $(dirname $(dirname $(dirname $(dirname $DIR)))))

    OUT_DIR="$OUTPUT_ROOT/$DATASET/$VARIANT/$SESSION"
    mkdir -p "$OUT_DIR"
    cp "$DIR/metrics.json" "$OUT_DIR"
    for f in "$DIR/renders"/*.png; do
        [ -f "$f" ] || break
        cp "$f" "$OUT_DIR"
    done
    for f in "$DIR"/*.mp4; do
        [ -f "$f" ] || break
        cp "$f" "$OUT_DIR"
    done
done