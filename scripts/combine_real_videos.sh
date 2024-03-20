#!/bin/bash
set -eux

BASELINE="$1"
OURS="$2"
INPUT_VIDEO="$3"
OUT_FILE="$4"
: "${ROTATED:=OFF}"
: "${FPS:=60}"

OVERLAY=overlay_images/overlay_1920x1280_rec.png
OVERLAY_INP=overlay_images/overlay_1920x1280_input_data.png

mkdir -p data/demo_videos

RAW_OUT="-c:v libx264 -crf 12 -qp 0 -bsf:v h264_mp4toannexb -f mpegts -hide_banner -loglevel error -y -avoid_negative_ts make_zero"
HI_Q_OUT="-bsf:a aac_adtstoasc -c:v libx264 -crf 22 -qp 0 -y -pix_fmt yuv420p"

tempfile=$(mktemp /tmp/video1_XXXXXX.ts)
tempfile_input_video=$(mktemp /tmp/video1_XXXXXX.ts)
tempfile_input_video2=$(mktemp /tmp/video2_XXXXXX.ts)

# ffmpeg -ss 2 -to 12 -i "$INPUT_VIDEO" -filter_complex "[0:v]setpts=8*PTS,fps=$FPS[v]" -map "[v]" -y $RAW_OUT $tempfile_input_video
ffmpeg -ss 4 -to 12 -i "$INPUT_VIDEO" -filter_complex "[0:v]setpts=2*PTS,fps=$FPS[v]" -map "[v]" -y $RAW_OUT $tempfile_input_video2

if [ "$ROTATED" = "ON" ]; then
    BASELINE_ROTATED=$(mktemp /tmp/video_rot_XXXXXX.ts)
    OURS_ROTATED=$(mktemp /tmp/video2_rot_XXXXXX.ts)

    ffmpeg -i "$OURS" -vf "transpose=1, crop=ih*3/4:ih" $RAW_OUT "$OURS_ROTATED"
    ffmpeg -i "$BASELINE" -vf "transpose=1, crop=ih*3/4:ih" $RAW_OUT "$BASELINE_ROTATED"

    ffmpeg -i "$tempfile_input_video2" \
        -i "$OVERLAY_INP" \
        -filter_complex \
        "[0:v]scale=1920:1280:force_original_aspect_ratio=decrease,pad=1920:1280:(ow-iw)/2:(oh-ih)/2[scaled];\
[1:v]crop=1800:1280:0:160[cropped];\
[scaled][cropped]overlay=120:0" \
        -y $RAW_OUT $tempfile_input_video

    ffmpeg \
        -i "$BASELINE_ROTATED" \
        -i "$OURS_ROTATED" \
        -i "$OVERLAY" \
        -filter_complex \
"[0:v]scale=-1:1280[left];\
[1:v]scale=-1:1280[right];\
[0:v]crop=iw/9:ih/12:iw*5/12:ih*5/12,scale=270:270[left_zoom];\
[1:v]crop=iw/9:ih/12:iw*5/12:ih*5/12,scale=270:270[right_zoom];\
[left][right]hstack[stacked];\
[stacked][left_zoom]overlay=W-w-270:H-h[right_zoomed];\
[right_zoomed][right_zoom]overlay=W-w:H-h[with_zooms];\
[2:v]crop=1920:1280:0:0[cropped];\
[with_zooms][cropped]overlay=0:0,fps=$FPS" \
        $RAW_OUT \
        -y \
        "$tempfile"
else
    BASELINE_ROTATED=$BASELINE
    OURS_ROTATED=$OURS

    ffmpeg -i "$tempfile_input_video2" -i "$OVERLAY_INP" -filter_complex "[0:v]crop=1920:1280:0:(ih-1280)/2[cropped];[cropped][1:v]overlay=0:0" -y $RAW_OUT $tempfile_input_video

    ffmpeg \
        -i "$BASELINE_ROTATED" \
        -i "$OURS_ROTATED" \
        -i "$OVERLAY" \
        -filter_complex "\
[0:v]crop=1920:1280:0:(ih-1280)/2[lcrop];\
[1:v]crop=1920:1280:0:(ih-1280)/2[rcrop];\
[lcrop]crop=iw/2:ih:0:0[left];\
[rcrop]crop=iw/2:ih:iw/2:0[right];\
[left][right]hstack[base];\
[0:v]crop=iw/12:ih/12:iw*5/12:ih*5/12,scale=360:270[left_zoom];\
[1:v]crop=iw/12:ih/12:iw*5/12:ih*5/12,scale=360:270[right_zoom];\
[base][left_zoom]overlay=W-w-360:H-h[right_zoomed];\
[right_zoomed][right_zoom]overlay=W-w:H-h[with_zooms];\
[with_zooms][2:v]overlay=0:0,fps=$FPS" \
        $RAW_OUT \
        -y \
        "$tempfile"
fi

ffmpeg -i "$tempfile_input_video" -i "$tempfile" -filter_complex \
    "[0:v][1:v]xfade=transition=fade:duration=1.5:offset=4[v]" \
    -map "[v]" -r 30 \
    -y $HI_Q_OUT "$OUT_FILE"
#ffmpeg  -f mpegts -i "concat:$tempfile_input_video|$tempfile" -y $HI_Q_OUT "$OUT_FILE"
