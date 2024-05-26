#!/bin/bash
set -eux

# Process raw input data. If set to OFF, then sai-cli and
# colmap-sai-cli-imgs intermediary datasets must have been
# fully generated or downloaded
: "${PROCESS_RAW:=ON}"

# Extra variants in the supplementary
: "${EXTRA_VARIANTS:=OFF}"

# Show preview in sai-cli
: "${PREVIEW:=ON}"

if [ $PREVIEW == "ON" ]; then
    PREVIEW_FLAG="--preview"
else
    PREVIEW_FLAG=""
fi

if [ $PROCESS_RAW == "ON" ]; then
	# Process and convert using the Spectacular AI SDK to get VIO velocity and pose estimates
	python process_sai_inputs.py $PREVIEW_FLAG
	# you can also run individual failing cases with: python run_colmap.py all --case=N
	python run_colmap.py all --max_retries=10
fi

rm -rf data/inputs-processed/colmap-sai-cli-vels*
rm -rf data/inputs-processed/colmap-sai-cli-orig-intrinsics*
rm -rf data/inputs-processed/sai-cli-blur-scored

# --- real data, COLMAP intrinsics
python combine.py all
python train_eval_split_by_blur_score.py colmap-sai-cli-vels all

# --- real data, factory intrinsics
python combine.py --keep_intrinsics all
python train_eval_split_by_blur_score.py colmap-sai-cli-orig-intrinsics all

# --- real data, calibrated intrinsics
rm -rf data/inputs-processed/colmap-sai-cli-calib-intrinsics*

for i in 1 2 3 4 5; do
	python combine.py --case=$i --keep_intrinsics --set_rolling_shutter_to=0.005
done

for i in 6 7 8; do
	python combine.py --case=$i --override_calibration=data/inputs-raw/spectacular-rec-extras/calibration/manual-calibration-result-pixel5.json
done

for i in 9 10 11; do
	python combine.py --case=$i --override_calibration=data/inputs-raw/spectacular-rec-extras/calibration/manual-calibration-result-s20.json
done

python train_eval_split_by_blur_score.py colmap-sai-cli-calib-intrinsics all

if [ $EXTRA_VARIANTS == "ON" ]; then
	rm -rf data/inputs-processed/colmap-sai-cli-no-blur-select-imgs*

	if [ $PROCESS_RAW == "ON" ]; then
		# --- real data, no blur score filter
		python process_sai_inputs.py --no_blur_score_filter $PREVIEW_FLAG
	fi

	# NOTE: run this until success
	python run_colmap.py --dataset=sai-cli-no-blur-select all --max_retries=10

	# --- real data, no blur score filter, COLMAP intrinsics
	python combine.py --dataset=sai-cli-no-blur-select all

	# --- real data, no blur score filter, factory intrinsics
	python combine.py --keep_intrinsics --dataset=sai-cli-no-blur-select all
fi

