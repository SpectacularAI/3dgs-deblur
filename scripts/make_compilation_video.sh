#!/bin/bash
set -eux

SRC_FOLDER="data/renders"
OUT_FOLDER="$SRC_FOLDER"

TMP_FOLDER=`mktemp -d`

RAW_OUT="-c:v libx264 -crf 12 -qp 0 -bsf:v h264_mp4toannexb -f mpegts -hide_banner -loglevel error -y -avoid_negative_ts make_zero"
HI_Q_OUT="-bsf:a aac_adtstoasc -c:v libx264 -crf 21 -qp 0 -y -pix_fmt yuv420p"

FPS=30
RESO="1920x1280"
TRANS_TIME=3.5
TRANS_TIME_SHORT=3

ffmpeg -i "$SRC_FOLDER/s20-sign.mp4" \
    -i "overlay_images/overlay_s20.png" \
    -filter_complex "[0:v][1:v]overlay=enable='between(t\,0,3)',fps=$FPS" \
    -ss 1.5 \
    -to 14.5 \
    -y $RAW_OUT "$TMP_FOLDER/s20.ts"

ffmpeg -i "$SRC_FOLDER/s20-bike.mp4" \
    -to 15 \
    -y $RAW_OUT "$TMP_FOLDER/s202.ts"

for case in iphone-lego1 iphone-pots2; do
    OVERLAY_BASE=overlay_images/overlay_${RESO}_splatfacto.png \
    OVERLAY_OURS=overlay_images/overlay_${RESO}_deblurred.png \
    SCALE="${RESO}" \
    TS_OUT=ON \
    ./scripts/combine_videos.sh \
        "$SRC_FOLDER/${case}_baseline.mp4" \
        "$SRC_FOLDER/${case}_motion_blur.mp4" \
        "$TMP_FOLDER/${case}.ts"
done

ffmpeg -i "$SRC_FOLDER/iphone-lego1-long.mp4" \
    -i "overlay_images/overlay_iphone.png" \
    -filter_complex "[0:v]scale=$RESO[scaled];[scaled][1:v]overlay=enable='between(t\,0,3)',fps=$FPS" \
    -to 16 \
    -y $RAW_OUT "$TMP_FOLDER/iphone.ts"

ffmpeg -i "$TMP_FOLDER/iphone-lego1.ts" \
    -i "overlay_images/overlay_iphone.png" \
    -filter_complex "[0:v]scale=$RESO[scaled];[scaled][1:v]overlay=enable='between(t\,0,3)',fps=$FPS" \
    -y $RAW_OUT "$TMP_FOLDER/iphone-short.ts"

ffmpeg -stream_loop 3 -i "$SRC_FOLDER/synthetic_mbrs_from_real_data_keep.mp4" \
    -i "overlay_images/title.png" \
    -filter_complex "[0:v][1:v]overlay,fps=$FPS,crop=1920:1280:0:80" -y $RAW_OUT "$TMP_FOLDER/compilation_title.ts"

ffmpeg -stream_loop 2 -i "$SRC_FOLDER/synthetic_mbrs_from_real_data_keep.mp4" \
    -i "overlay_images/title.png" \
    -filter_complex "[0:v][1:v]overlay,fps=$FPS,crop=1920:1280:0:80" -y $RAW_OUT "$TMP_FOLDER/compilation_title_short.ts"

ffmpeg -stream_loop 3 -i "$SRC_FOLDER/synthetic_mbrs_from_real_data_keep.mp4" \
    -i "overlay_images/authors.png" \
    -filter_complex "[0:v][1:v]overlay,fps=$FPS,crop=1920:1280:0:80" -y $RAW_OUT "$TMP_FOLDER/compilation_authors.ts"

HW=960
HH=640
HALFRESO="${HW}x${HH}"

for DS in mb rs posenoise; do
    case $DS in

    mb)
        TEXT=deblurred
        ;;

    rs)
        TEXT=compensated
        ;;

    posenoise)
        TEXT=optimized
        ;;
        
    esac

    for case in cozyroom factory tanabata pool; do
        OVERLAY_BASE=overlay_images/overlay_${RESO}_splatfacto.png \
        OVERLAY_OURS=overlay_images/overlay_${RESO}_${TEXT}.png \
        SCALE="${RESO}" \
        TS_OUT=ON \
        ./scripts/combine_videos.sh \
            "$SRC_FOLDER/synthetic-${case}-${DS}-baseline-${HALFRESO}.mp4" \
            "$SRC_FOLDER/synthetic-${case}-${DS}-ours-${HALFRESO}.mp4" \
            "$TMP_FOLDER/base_vs_ours_${DS}_${case}.ts"
    done

    for case in baseline ours; do
        ffmpeg \
            -i "$SRC_FOLDER/synthetic-cozyroom-${DS}-${case}-${HALFRESO}.mp4" \
            -i "$SRC_FOLDER/synthetic-factory-${DS}-${case}-${HALFRESO}.mp4" \
            -i "$SRC_FOLDER/synthetic-tanabata-${DS}-${case}-${HALFRESO}.mp4" \
            -i "$SRC_FOLDER/synthetic-pool-${DS}-${case}-${HALFRESO}.mp4" \
            -filter_complex "
                nullsrc=size=$RESO [base];
                [0:v] scale=$HALFRESO [upperleft];
                [1:v] scale=$HALFRESO [upperright];
                [2:v] scale=$HALFRESO [lowerleft];
                [3:v] scale=$HALFRESO [lowerright];
                [base][upperleft] overlay=shortest=1 [tmp1];
                [tmp1][upperright] overlay=shortest=1:x=$HW [tmp2];
                [tmp2][lowerleft] overlay=shortest=1:y=$HH [tmp3];
                [tmp3][lowerright] overlay=shortest=1:x=$HW:y=$HH" \
            -y $RAW_OUT "$TMP_FOLDER/${DS}_${case}_mosaic.ts"
    done

    OVERLAY_BASE=overlay_images/overlay_${RESO}_splatfacto.png \
    OVERLAY_OURS=overlay_images/overlay_${RESO}_${TEXT}.png \
    SCALE="1920x1280" \
    TS_OUT=ON \
    ./scripts/combine_videos.sh \
        "$TMP_FOLDER/${DS}_baseline_mosaic.ts" \
        "$TMP_FOLDER/${DS}_ours_mosaic.ts" \
        "$TMP_FOLDER/base_vs_ours_${DS}.ts" 
done

for DS in motion_blur rolling_shutter; do
    ffmpeg -i "$SRC_FOLDER/synthetic_${DS}_example_${HALFRESO}.mp4" \
        -i "overlay_images/overlay_${DS}.png" \
        -filter_complex "[1:v]crop=1920:1280:0:80[cropped];[0:v]scale=$RESO,fps=$FPS[o];[o][cropped]overlay" \
        -to $TRANS_TIME \
        -y $RAW_OUT "$TMP_FOLDER/compilation_${DS}.ts"
    ffmpeg -i "$SRC_FOLDER/synthetic_${DS}_example_${HALFRESO}.mp4" \
        -i "overlay_images/overlay_${DS}.png" \
        -filter_complex "[1:v]crop=1920:1280:0:80[cropped];[0:v]scale=$RESO,fps=$FPS[o];[o][cropped]overlay" \
        -to $TRANS_TIME_SHORT \
        -y $RAW_OUT "$TMP_FOLDER/compilation_${DS}_short.ts"
done

ffmpeg -i "$TMP_FOLDER/base_vs_ours_posenoise.ts" \
    -i "overlay_images/overlay_posenoise.png" \
    -filter_complex "[1:v]crop=1920:1280:0:80[cropped];[0:v][cropped]overlay" \
    -to 6 \
    -y $RAW_OUT "$TMP_FOLDER/compilation_posenoise.ts"

OUT_FILE="$OUT_FOLDER/compilation_demo.mp4"
ffmpeg  -f mpegts -i "concat:$TMP_FOLDER/compilation_title.ts\
|$TMP_FOLDER/compilation_motion_blur.ts\
|$TMP_FOLDER/base_vs_ours_mb.ts\
|$TMP_FOLDER/base_vs_ours_mb.ts\
|$TMP_FOLDER/compilation_rolling_shutter.ts\
|$TMP_FOLDER/base_vs_ours_rs.ts\
|$TMP_FOLDER/base_vs_ours_rs.ts\
|$TMP_FOLDER/compilation_posenoise.ts\
|$TMP_FOLDER/iphone.ts\
|$TMP_FOLDER/iphone-pots2.ts\
|$TMP_FOLDER/s20.ts\
|$TMP_FOLDER/s202.ts\
|$TMP_FOLDER/compilation_authors.ts" \
    -y $HI_Q_OUT "$OUT_FILE"

OUT_FILE_SHORT="$OUT_FOLDER/compilation_demo_short.mp4"
ffmpeg  -f mpegts -i "concat:$TMP_FOLDER/compilation_title_short.ts\
|$TMP_FOLDER/compilation_rolling_shutter_short.ts\
|$TMP_FOLDER/base_vs_ours_rs_cozyroom.ts\
|$TMP_FOLDER/compilation_motion_blur_short.ts\
|$TMP_FOLDER/base_vs_ours_mb_factory.ts\
|$TMP_FOLDER/compilation_posenoise.ts\
|$TMP_FOLDER/iphone-short.ts\
|$TMP_FOLDER/iphone-pots2.ts\
|$TMP_FOLDER/s20.ts" \
    -y $HI_Q_OUT "$OUT_FILE_SHORT"

rm -rf "$TMP_FOLDER"
