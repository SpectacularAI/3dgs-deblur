#!/bin/bash
set -eux

# Prerequisites: sai-cli and colmap-sai-cli-imgs intermediary datasets
# have been created and are complete (see README.md for instructions)

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

# Extra variants in the supplementary
: "${EXTRA_VARIANTS:=OFF}"
if [ $EXTRA_VARIANTS == "ON" ]; then
	# --- real data, no blur score filter
	python process_sai_inputs.py --no_blur_score_filter --preview
	# NOTE: run this until success
	python run_colmap.py --dataset=sai-cli-no-blur-select all

	rm -rf data/inputs-processed/colmap-sai-cli-no-blur-select-imgs*

	# --- real data, no blur score filter, COLMAP intrinsics
	python combine.py --dataset=sai-cli-no-blur-select all

	# --- real data, no blur score filter, factory intrinsics
	python combine.py --keep_intrinsics --dataset=sai-cli-no-blur-select all
fi

