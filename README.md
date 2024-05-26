# Gaussian Splatting on the Move: <br> Blur and Rolling Shutter Compensation for Natural Camera Motion

[![arXiv preprint](https://img.shields.io/badge/arXiv-2403.13327-b31b1b?logo=arxiv&logoColor=red)](https://arxiv.org/abs/2403.13327)

## Installation

Prerequisites: run on a Linux system with a recent NVidia RTX GPU with at least 8 GB of VRAM.
Git must be installed.

 1. Activate a Conda environment with PyTorch that [supports Nerfstudio](https://github.com/nerfstudio-project/nerfstudio/?tab=readme-ov-file#dependencies)
 2. Possibly required, depending on your environment: `conda install -c conda-forge gcc=12.1.0`
 3. Run `./scripts/install.sh` (see steps within if something goes wrong)

## Training with custom data

**Custom video data** (_new in version 2_): The method can now be used for motion blur compensation with plain video data as follows 

    ./scripts/process_and_train_video.sh /path/to/video.mp4

or for rolling shutter compensation as

    ROLLING_SHUTTER=ON ./scripts/process_and_train_video.sh /path/to/video.mp4

Currently simultaneous motion blur and rolling-shutter compensation is only possible with known readout and exposure times. The easiest way to achieve this is using the Spectacular Rec application to record the data (see below).

**Spectacular Rec app** ([v1.0.0+ for Android](https://play.google.com/store/apps/details?id=com.spectacularai.rec), [v1.2.0+ for iOS](https://apps.apple.com/us/app/spectacular-rec/id6473188128)) is needed for simultaneous rolling shutter and motion blur compensation. This approach is also expected to give the best results if the data collection app can be chosen, since it also allows automatic blurry frame filtering and VIO-based velocity initialization, both of which improve the final reconstruction quality. Instructions below.

First, download and extract a recording created using the app, e.g., `/PATH/TO/spectacular-rec-MY_RECORDING`.

Then process as

    ./scrpts/process_and_train_sai_custom.sh /PATH/TO/spectacular-rec-MY_RECORDING

or, for a faster version:

    SKIP_COLMAP=ON ./scrpts/process_and_train_sai_custom.sh /PATH/TO/spectacular-rec-MY_RECORDING

See the contents of the script for more details.

**Comparison videos** To train a custom recording with and without motion blur compensation and render a video comparing the two, use this script:

 * motion blur OR rolling shutter, COLMAP-based, from video:

        ./scripts/render_and_compile_comparison_video.sh /path/to/video.mp4
        ROLLING_SHUTTER=ON ./scripts/render_and_compile_comparison_video.sh /path/to/video.mp4

 * motion blur AND rolling shutter compensations (needs Spectacular Rec data)
 
        ./scripts/render_and_train_comparison_sai_custom.sh /PATH/TO/spectacular-rec-MY_RECORDING

## Benchmark data

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

Additionally, any folder of the form `data/inputs-processed/CASE` can be trained directly with Nerfstudio
using the `ns-train splatfacto --data data/inputs-processed/CASE ...`. Use `--help` and see `train.py` for
the recommended parameters.

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

 * Created by `train.py --render_images ...`: Renders of evaluation images and predictions are available in `outputs/DATASET/VARIANT/splatfacto/TIMESTAMP` (`/renders`, or `/demo_video*.mp4` if `render_video.py` has been run, see below)
 * Demo videos: see `render_video.py` and `scripts/render_and_combine_comparison_video.sh`

## Processing the raw benchmark input data

This method also creates the extra variants discussed in the appendix/supplementary material of the paper,
as well as all the relevant synthetic data variants.

### Synthetic data

For synthetic data, we use different re-rendered versions of the [Deblur-NeRF](https://limacv.github.io/deblurnerf/) synthetic dataset.
Note that there exists several, slightly different variation, which need to be trained with correct parameters for optimal results.

**Our Deblur-NeRF re-render** (uses $\gamma = 2.2$): Download and process as:

    python download_data.py --dataset synthetic-raw
    python process_synthetic_inputs.py

**Other variants**

 1. Download the data and extract as `inputs-raw/FOLDER_NAME` (see options below)
 2. Run

        python process_deblur_nerf_inputs.py --dataset=FOLDER_NAME --manual_point_cloud all

This creates a dataset called `colmap-DATASET-synthetic-novel-view-manual-pc`
Note that it may be necessary to run the last command multiple times until COLMAP succeeds
in all cases (see also the `--case=N` argument in the script).

Supported datasets (TODO: a bit messy):

 * Original Deblur-NeRF: `FOLDER_NAME` = `synthetic_camera_motion_blur`. Uses $\gamma = 2.2$.
 * [BAD-NeRF](https://wangpeng000.github.io/BAD-NeRF/) re-render: `FOLDER_NAME` = `nerf_llff_data`. Uses $\gamma = 1$.
 * [BAD-Gaussians](https://lingzhezhao.github.io/BAD-Gaussians/) re-render: `FOLDER_NAME` = `bad-nerf-gtK-colmap-nvs`
 
The last two are very similar except for the "Tanabata" scene, which is broken in the BAD-NeRF version:
the underlying 3D model is slightly different in the (sharp) and training (blurry) images (objects moved around).

### Smartphone data

Download as:

    python download_data.py --dataset sai-raw

and then process and convert using the following script:

    ./scripts/process_smartphone_dataset.sh
    # or 
    # EXTRA_VARIANTS=ON ./scripts/process_smartphone_dataset.sh

Note: all the components in this pipeline are not guaranteed to be deterministic, especially when executed on different machines.
Especially the COLMAP has a high level of randomness.

## Changelog

### Version 2 (2024-05)

 * Angular and linear velocities added as optimizable variables, which can be initialized to zero if VIO-estimated velocity data is not available (i.e., no IMU data available)
 * Added `--optimize-eval-cameras` mode, which allows optimizing evaluation camera poses and velocities (if `--optimize-eval-velocities=True`) without back-propagating information to the 3DSG reconstruction. This replaces the previous two-phase optimization mode (called "rolling shutter pose optimization" in the first paper revision)
 * Method can be run in motion blur OR rolling-shutter mode form plain video without a known exposure or readout times. Added a helper script `process_and_train_video.sh` for this.
 * Rebased on Nerfstudio version 1.1.0 and `gsplat` [409bcd3c](https://github.com/nerfstudio-project/gsplat/commit/409bcd3cf63491710444e60c29d3c44608d8eafd) (based on 0.1.11)
 * Fixed a bug in pixel velocity formulas
 * Tuned hyper-parameters (separate parameters for synthetic and real data)
 * Using [optimizable background color](https://github.com/nerfstudio-project/nerfstudio/pull/3100) by [KevinXu02](https://github.com/KevinXu02) for synthetic data
 * Using $\gamma \neq 1$ and `--min-rgb-level` only when motion blur compensation is enabled (for a more fair comparison to Splatfacto)
 * Added conversion scripts for other common Deblur-NeRF dataset variants

### Version 1 (2024-03)

Initial release where IMU data was mandatory to run the method, and the uncertainties in VIO-estimated velocities were addressed with a custom regularization scheme (see §3.6 in the [first revision of the paper](https://arxiv.org/pdf/2403.13327v1)).
Based on Nerfstudio version 1.0.2 and `gsplat` 0.1.8.

## License

The code in this repository (except the `gh-pages` website branch) is licensed under Apache 2.0.
See `LICENSE` and `NOTICE` files for more information.

For the source code of the website and its license, see the [`gh-pages` branch](https://github.com/SpectacularAI/3dgs-deblur/tree/gh-pages).

The licenses of the datasets (CC BY-SA 4.0 & CC BY 4.0) are detailed on the Zenodo pages.
