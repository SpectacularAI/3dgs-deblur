#!/bin/bash
set -eux

# --- synthetic data
python process_synthetic_inputs.py

# --- real data
python process_inputs.py --preview
# NOTE: this has some level of randomness. COLMAP may or may
# not fail for some of the sequences, but should eventyally succeed for
# the included sequences after a few retries.
python run_colmap.py all

rm -rf data/inputs-processed/colmap-sai-cli-vels*
rm -rf data/inputs-processed/colmap-sai-cli-orig-intrinsics*
rm -rf data/inputs-processed/sai-cli-blur-scored

# --- real data, COLMAP intrinsics
python combine.py all
python train_eval_split_by_blur_score.py colmap-sai-cli-vels

# --- real data, factory intrinsics
python combine.py --keep_intrinsics all
python train_eval_split_by_blur_score.py colmap-sai-cli-orig-intrinsics all

# --- real data, calibrated intrinsics
rm -rf data/inputs-processed/colmap-sai-cli-calib-intrinsics*

for i in 1 2 3 4 5; do
	python combine.py --case=$i --keep_intrinsics --set_rolling_shutter_to=0.005
done

for i in 6 7 8 9; do
	python combine.py --case=$i --override_calibration=data/inputs-raw/override-calib-pixel5.json
done

for i in 10 11 12 13 14; do
	python combine.py --case=$i --override_calibration=data/inputs-raw/override-calib-samsung.json
done

python train_eval_split_by_blur_score.py colmap-sai-cli-calib-intrinsics all

# --- real data, no blur score filter
python process_inputs.py --no_blur_score_filter --preview
python run_colmap.py --dataset=sai-cli-no-blur-select all

rm -rf data/inputs-processed/colmap-sai-cli-no-blur-select-imgs*

# --- real data, no blur score filter, COLMAP intrinsics
python combine.py --dataset=sai-cli-no-blur-select all

# --- real data, no blur score filter, factory intrinsics
python combine.py --keep_intrinsics --dataset=sai-cli-no-blur-select all