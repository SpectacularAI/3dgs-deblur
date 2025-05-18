#!/bin/bash
# Script to launch mido_process_train_sai.py in the background using the comfy conda environment
# All output is logged to data/logs/mido_process_train_sai_main.log

# Activate conda and the comfy environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate 3dgs

# Run the python script in the background, redirecting output to a main log
nohup python mido_process_train_sai.py >> mido_process_train_sai_main.log 2>&1 &
