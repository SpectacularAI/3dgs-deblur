"""Load g model and render all outputs to disc"""

from dataclasses import dataclass
from pathlib import Path
import torch
import tyro
import os
import numpy as np
import shutil

from nerfstudio.cameras.cameras import Cameras
from nerfstudio.models.splatfacto import SplatfactoModel
from nerfstudio.utils.eval_utils import eval_setup
from nerfstudio.utils import colormaps
from nerfstudio.data.datasets.base_dataset import InputDataset
from PIL import Image
from torch import Tensor

from typing import List, Literal, Optional, Union

def save_img(image, image_path, verbose=True) -> None:
    """helper to save images

    Args:
        image: image to save (numpy, Tensor)
        image_path: path to save
        verbose: whether to print save path

    Returns:
        None
    """
    if image.shape[-1] == 1 and torch.is_tensor(image):
        image = image.repeat(1, 1, 3)
    if torch.is_tensor(image):
        image = image.detach().cpu().numpy() * 255
        image = image.astype(np.uint8)
    if not Path(os.path.dirname(image_path)).exists():
        Path(os.path.dirname(image_path)).mkdir(parents=True)
    im = Image.fromarray(image)
    if verbose:
        print("saving to: ", image_path)
    im.save(image_path)

# Depth Scale Factor m to mm
SCALE_FACTOR = 0.001
SAVE_RAW_DEPTH = False

def save_depth(depth, depth_path, verbose=True, scale_factor=SCALE_FACTOR) -> None:
    """helper to save metric depths

    Args:
        depth: image to save (numpy, Tensor)
        depth_path: path to save
        verbose: whether to print save path
        scale_factor: depth metric scaling factor

    Returns:
        None
    """
    if torch.is_tensor(depth):
        depth = depth.float() / scale_factor
        depth = depth.detach().cpu().numpy()
    else:
        depth = depth / scale_factor
    if not Path(os.path.dirname(depth_path)).exists():
        Path(os.path.dirname(depth_path)).mkdir(parents=True)
    if verbose:
        print("saving to: ", depth_path)
    np.save(depth_path, depth)

def save_outputs_helper(
    rgb_out: Optional[Tensor],
    gt_img: Optional[Tensor],
    depth_color: Optional[Tensor],
    depth_gt_color: Optional[Tensor],
    depth_gt: Optional[Tensor],
    depth: Optional[Tensor],
    normal_gt: Optional[Tensor],
    normal: Optional[Tensor],
    render_output_path: Path,
    image_name: Optional[str],
) -> None:
    """Helper to save model rgb/depth/gt outputs to disk

    Args:
        rgb_out: rgb image
        gt_img: gt rgb image
        depth_color: colored depth image
        depth_gt_color: gt colored depth image
        depth_gt: gt depth map
        depth: depth map
        render_output_path: save directory path
        image_name: stem of save name

    Returns:
        None
    """
    if image_name is None:
        image_name = ""

    if rgb_out is not None and gt_img is not None:
        # easier consecutive compare
        save_img(rgb_out, os.getcwd() + f"/{render_output_path}/{image_name}_pred.png", False)
        save_img(gt_img, os.getcwd() + f"/{render_output_path}/{image_name}_gt.png", False)

    if depth_color is not None:
        save_img(
            depth_color,
            os.getcwd()
            + f"/{render_output_path}/pred/depth/colorised/{image_name}.png",
            False,
        )
    if depth_gt_color is not None:
        save_img(
            depth_gt_color,
            os.getcwd() + f"/{render_output_path}/gt/depth/colorised/{image_name}.png",
            False,
        )
    if depth_gt is not None:
        # save metric depths
        save_depth(
            depth_gt,
            os.getcwd() + f"/{render_output_path}/gt/depth/raw/{image_name}.npy",
            False,
        )

    if SAVE_RAW_DEPTH:
        if depth is not None:
            save_depth(
                depth,
                os.getcwd() + f"/{render_output_path}/pred/depth/raw/{image_name}.npy",
                False,
            )

    if normal is not None:
        save_normal(
            normal,
            os.getcwd() + f"/{render_output_path}/pred/normal/{image_name}.png",
            verbose=False,
        )

    if normal_gt is not None:
        save_normal(
            normal_gt,
            os.getcwd() + f"/{render_output_path}/gt/normal/{image_name}.png",
            verbose=False,
        )

@dataclass
class RenderModel:
    """Render outputs of a GS model."""

    load_config: Path = Path("outputs/")
    """Path to the config YAML file."""
    output_dir: Path = Path("./data/renders/")
    """Path to the output directory."""
    set: Literal["train", "eval"] = "eval"
    """Dataset to test with (train or eval)"""
    output_same_dir: bool = True
    """Output to the subdirectory of the load_config path"""

    def main(self):
        if self.output_same_dir:
            self.output_dir = os.path.join(os.path.dirname(self.load_config), 'renders')

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)
        print('writing %s' % str(self.output_dir))

        _, pipeline, _, _ = eval_setup(self.load_config)

        assert isinstance(pipeline.model, SplatfactoModel)

        model: SplatfactoModel = pipeline.model
        dataset: InputDataset

        with torch.no_grad():
            if self.set == "train":
                dataset = pipeline.datamanager.train_dataset
                images = pipeline.datamanager.cached_train
            elif self.set == "eval":
                dataset = pipeline.datamanager.eval_dataset
                images = pipeline.datamanager.cached_eval
            else:
                raise RuntimeError("Invalid set")
        
            cameras: Cameras = dataset.cameras  # type: ignore
            for image_idx in range(len(dataset)):  # type: ignore
                data = images[image_idx]

                # process batch gt data
                mask = None
                if "mask" in data:
                    mask = data["mask"]

                gt_img = 256 - data["image"] # not sure why negative
                if "sensor_depth" in data:
                    depth_gt = data["sensor_depth"]
                    depth_gt_color = colormaps.apply_depth_colormap(
                        data["sensor_depth"]
                    )
                else:
                    depth_gt = None
                    depth_gt_color = None
                if "normal" in data:
                    normal_gt = data["normal"]
                else:
                    normal_gt = None

                # process pred outputs
                camera = cameras[image_idx : image_idx + 1].to("cpu")
                outputs = model.get_outputs_for_camera(camera=camera, camera_idx=image_idx)

                rgb_out, depth_out = outputs["rgb"], outputs["depth"]

                normal = None
                if "normal" in outputs:
                    normal = outputs["normal"]

                seq_name = Path(dataset.image_filenames[image_idx])
                image_name = f"{seq_name.stem}"

                depth_color = colormaps.apply_depth_colormap(depth_out)
                depth = depth_out.detach().cpu().numpy()

                if mask is not None:
                    rgb_out = rgb_out * mask
                    gt_img = gt_img * mask
                    if depth_color is not None:
                        depth_color = depth_color * mask
                    if depth_gt_color is not None:
                        depth_gt_color = depth_gt_color * mask
                    if depth_gt is not None:
                        depth_gt = depth_gt * mask
                    if depth is not None:
                        depth = depth * mask
                    if normal_gt is not None:
                        normal_gt = normal_gt * mask
                    if normal is not None:
                        normal = normal * mask

                # save all outputs
                save_outputs_helper(
                    rgb_out,
                    gt_img,
                    depth_color,
                    depth_gt_color,
                    depth_gt,
                    depth,
                    normal_gt,
                    normal,
                    self.output_dir,
                    image_name,
                )


if __name__ == "__main__":
    tyro.cli(RenderModel).main()
