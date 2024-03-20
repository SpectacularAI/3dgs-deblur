#!/bin/bash
set -eux

BASELINE="$1"
OURS="$2"
OUT_FILE="$3"
: "${SCALE:=600x400}"
: "${OVERLAY_BASE:=overlay_images/overlay_600x400_splatfacto.png}"
: "${OVERLAY_OURS:=overlay_images/overlay_600x400_deblurred.png}"
: "${TS_OUT:=OFF}"

RAW_OUT="-c:v libx264 -crf 12 -qp 0 -bsf:v h264_mp4toannexb -f mpegts -hide_banner -loglevel error -y -avoid_negative_ts make_zero"
HI_Q_OUT="-bsf:a aac_adtstoasc -c:v libx264 -crf 21 -qp 0 -y -pix_fmt yuv420p"

if [ "$TS_OUT" = "ON" ]; then
    OUT_FMT=$RAW_OUT
else
    OUT_FMT=$HI_Q_OUT
fi

LEN=8

ffmpeg \
    -i "$OURS" \
    -i "$BASELINE" \
    -i "$OVERLAY_OURS" \
    -i "$OVERLAY_BASE" \
    -filter_complex \
"[0:v]scale=$SCALE[oursscaled];\
 [1:v]scale=$SCALE[basescaled];\
 [oursscaled][2:v]overlay[ours1];\
 [basescaled][3:v]overlay[base1];\
 [ours1]setpts=PTS-STARTPTS[base];\
 [base1]setpts=PTS-STARTPTS[overlay];\
 color=0x00000000:s=$SCALE:d=$LEN,format=rgba[black];\
 color=0xffffffff:s=$SCALE:d=$LEN,format=rgba[white];\
 [black][white]blend=all_expr='if(lte(X,W*abs(1-T/$LEN*2)),B,A)':shortest=1[mask];\
 [overlay][mask]alphamerge[overlayalpha]; \
 [base][overlayalpha]overlay,fps=30" \
    $OUT_FMT \
    -y \
    "$OUT_FILE"