# Gaussian Splatting on the Move: <br> Blur and Rolling Shutter Compensation for Natural Camera Motion

[![arXiv preprint](https://img.shields.io/badge/arXiv-2403.13327-b31b1b?logo=arxiv&logoColor=red)](https://arxiv.org/abs/2403.13327)

## Installation

Prerequisites: run on a Linux system with a recent NVidia RTX GPU with at least 8 GB of VRAM.
Git must be installed.

 1. Activate a Conda environment with PyTorch that [supports Nerfstudio](https://github.com/nerfstudio-project/nerfstudio/?tab=readme-ov-file#dependencies)
 2. Possibly required, depending on your environment: `conda install -c conda-forge gcc=12.1.0`
 3. Run `./scripts/install.sh` (see steps within if something goes wrong)

## Data

[![Smartphone data](https://zenodo.org/badge/DOI/10.5281/zenodo.10848124.svg)](https://doi.org/10.5281/zenodo.10848124)
[![Synthetic data](https://zenodo.org/badge/DOI/10.5281/zenodo.10847884.svg)](https://doi.org/10.5281/zenodo.10847884)

The inputs directly trainable with our fork of Nerfstudio are stored in `data/inputs-processed` folder.
Its subfolders are called "datasets" in these scripts.

The data can be automatically downloaded by first installing: `pip install unzip` and then running

    python download_data.py --dataset synthetic
    # or 'sai' for processed real world smartphone data

<details>
<summary> The data folder structure is as follows: </summary>
<pre>
<code>
<3dgs-deblur>
|---data
    |---inputs-processed
        |---colmap-sai-cli-vels-blur-scored/
            |---iphone-lego1
                |---images
                    |---image 0
                    |---image 1
                    |---...
                |---sparse_pc.ply
                |---transforms.json
            |---...
        |---synthetic-mb
            |---cozyroom
                |---images
                    |---image 0
                    |---image 1
                    |---...
                |---sparse_pc.ply
                |---transforms.json
            |---...
        |---...
|---...
</code>
</pre>
</details>

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

## Processing the raw input data

This method also creates the extra variants discussed in the appendix/supplementary material of the paper.

**Synthetic data**: Download and process as

    python download_data.py --dataset synthetic-raw
    python process_synthetic_inputs.py

**Smartphone data**: Download as:

    python download_data.py --dataset sai-raw

and then process with the following steps

 1. Process and convert using the Spectacular AI SDK to get VIO velocity and pose estimates (`--preview` is optional). Creates a dataset called `sai-cli`:

        python process_sai_inputs.py --preview

 2. Run COLMAP. NOTE: this has some level of randomness. COLMAP may or may not fail for some of the sequences, but should eventyally succeed for the included sequences after a few retries. Run until ALL sequences succeed. See also the `python run_colmap.py` to list cases and `python run_colmap.py --case=N` to run a specific case. Creates a dataset called `colmap-sai-cli-imgs`.

        python run_colmap.py all

 3. Create the other variants by combining and augmenting the above two by running:

        ./scripts/create_smartphone_variants.sh
        # or 
        # EXTRA_VARIANTS=ON ./scripts/create_smartphone_variants.sh

Note: all the components in this pipeline are not guaranteed to be deterministic, especially when executed on different machines.

## Training with custom data

The method can be also be used with custom data recorded using the Spectacular Rec app ([v1.0.0+ for Android](https://play.google.com/store/apps/details?id=com.spectacularai.rec), [v1.2.0+ for iOS](https://apps.apple.com/us/app/spectacular-rec/id6473188128)).

First, download and extract a recording created using the app, e.g., `/PATH/TO/spectacular-rec-MY_RECORDING`.

**iOS cases** (short rolling shutter read-out): Process as

    ./scrpts/process_and_train_sai_custom_mb.sh /PATH/TO/spectacular-rec-MY_RECORDING

**Android** (long rolling-shutter readout). The recommended mode is:

    ./scripts/process_and_train_sai_custom_mbrs_pose_opt.sh

See the contents of the script for more details.

Additionally, any folder of the form `data/inputs-processed/CASE` can be trained directly with Nerfstudio
using the `ns-train splatfacto --data data/inputs-processed/CASE ...`. Use `--help` and see `train.py` for
the recommended parameters.

## License

The code in this repository (except the `gh-pages` website branch) is licensed under Apache 2.0.
See `LICENSE` and `NOTICE` files for more information.

For the source code of the website and its license, see the [`gh-pages` branch](https://github.com/SpectacularAI/3dgs-deblur/tree/gh-pages).

The licenses of the datasets (CC BY-SA 4.0 & CC BY 4.0) are detailed on the Zenodo pages.
