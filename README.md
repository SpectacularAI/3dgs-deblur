 # Gaussian Splatting on the Move
 **Blur and Rolling Shutter Compensation for Natural Camera Motion**

## Installation

Prerequisites: run on a Linux system with a recent NVidia RTX GPU with at least 8 GB of VRAM.
Git must be installed on the system.

 1. Activate a Conda environment with PyTorch that [supports Nerfstudio](https://github.com/nerfstudio-project/nerfstudio/?tab=readme-ov-file#dependencies)
 2. Possibly required, depending on your environment: `conda install -c conda-forge gcc=12.1.0`
 3. Run `./scripts/install.sh` (see steps within if something goes wrong)

## Data

### Raw inputs

Assumed to be in the directory `data/inputs-raw`. Processed by running `./scripts/process.sh`.

Another option is directly using the processed data, which is trainable with Nerfstudio.

### Processed inputs

The inputs directly trainable with our fork of Nerfstudio are in `data/inputs-processed`.
Its subfolders are called "datasets" in these scripts.

## Training

Example: List trainable variants for the `synthetic-mb` dataset:

    python train.py --dataset=synthetic-mb

Train a single variant

    python train.py --dataset=synthetic-mb --case=2

Common useful options:

 * `--dry_run`
 * `--preview` (show Viser during training)

**Second pass** for `pose_opt` variants: After training all the relevant `pose_opt` variants with the `--train_all` flag, e.g.,

    python train.py --dataset=synthetic-posenoise --train_all --case=2

run, e.g.,

    python combine.py \
        --dataset=synthetic-posenoise \
        --pose_opt_pass_dir data/outputs/synthetic-posenoise/pose_opt-train_all \
        --case=1

This creates new datasets in `input-processed/` with `2nd-pass` in their name. These can be trained again with `train.py`:

    python train.py --dataset=synthetic-posenoise-2nd-pass --case=1

If _all_ relevant first pass runs have been completed, you can also run `./scripts/process_2nd_pass.sh`,
which creates all the corresponding second pass datasets.

## Viewing the results

Results are written to `data/outputs/` by dataset. You can also run these on another machine
and download these results on your machine. All of the below commands should then work for
locally examining the results.

### Numeric

List all numeric results

    python parse_outputs.py

... or export to CSV

    python parse_outputs.py -f csv > data/results.csv

### Visualizations

Off-the-shelf:

 * Viser: `ns-viewer --load-config outputs/DATASET/VARIANT/splatfacto/TIMESTAMP/config.yml` (show actual results)
 * Tensorboard: `tensorboard --logdir outputs/DATASET/VARIANT/splatfacto/TIMESTAMP` (prerequisite `pip install tensorboard`)

Custom:

 * Automatically created by `train.py`: Renders of evaluation images and predictions are available in `outputs/DATASET/VARIANT/splatfacto/TIMESTAMP` (`/renders`, or `/demo_video*.mp4` if `render_video.py` has been run, see below)
 * Demo videos: see `render_video.py`.

## Training with new recordings directly

First run `sai-cli process` to select key frames and compute their poses and velocities:

    sai-cli process /PATH/TO/spectacular-rec_TIMESTAMP/ data/inputs-processed/misc/my_model --preview3d --preview

The train with all features enabled (example):

    ns-train splatfacto --data data/inputs-processed/misc/my_model \
        --output-dir data/outputs/misc \
        --pipeline.model.camera-optimizer.mode=SO3xR3 \
        --vis=viewer+tensorboard \
        --viewer.quit-on-train-completion True

Monitoring the training process from another terminal 
See `ns-train` output for the actual folder name

    tensorboard --logdir outputs/my_model/splatfacto/TIMESTAMP

# License

The code in this repository (except. the `gh-pages` website branch) is licensed under Apache 2.0.
See `LICENSE` and `NOTICE` files for more information.

For the source code of the website and its license, see the [`gh-pages` branch](https://github.com/SpectacularAI/3dgs-deblur/tree/gh-pages).
