"""Script to download the datasets."""
import os
from pathlib import Path
from typing import Literal

import gdown
import tyro
from dataclasses import dataclass

@dataclass
class DownloadProcessedData:
    save_dir: Path = Path(os.getcwd() + "/data")
    """Save directory. Default /data."""
    dataset: Literal[
        "synthetic-mb",
        "synthetic-rs",
        "synthetic-posenoise",
        "spectacular-rec",
        "deblurnerf_dataset_sai",

        "synthetic-all",
        "processed-all",
        "raw-all",

    ] = "synthetic-all"
    """Dataset download name. Set to 'synthetic-all' to download all synthetic data."""

    def main(self):
        urls = {
            "inputs-processed": {
                "synthetic-mb": "https://drive.google.com/drive/folders/1alEussfTV5f8rwKufQ0E_W86lnoFyFSG?usp=drive_link",
                "synthetic-rs": "https://drive.google.com/drive/folders/1b6ziMo2tKFswR85Rr3l0AB18VuMAXqOe?usp=drive_link",
                "synthetic-posenoise": "https://drive.google.com/drive/folders/1L0AwtJoLOERrkDsqSEGT8TqGRAibLNHP?usp=drive_link",
                "colmap-sai-cli-calib-intrinsics-blur-scored": "https://drive.google.com/drive/folders/1KM72Y92DFayJsw1qBDIMAx3z-TqFrsjQ?usp=drive_link"
            },
            "inputs-raw": {
                "spectacular-rec": "https://drive.google.com/drive/folders/1Fms67IPzdblI44rFZfazhLdrxfKH3sEv?usp=drive_link",
                "deblurnerf_dataset_sai": "https://drive.google.com/drive/folders/1TPGl_Q40UDVh8_pW4cAqSnPPVeJEFxwx?usp=drive_link"
            }
        }

        def download_dataset(dataset):
            for subfolder, sub_urls in urls.items():
                if dataset not in sub_urls: continue

                print(f"Downloading {subfolder}/{dataset}")
                save_dir = self.save_dir / subfolder / Path(dataset)
                save_dir.mkdir(parents=True, exist_ok=True)
                gdown.download_folder(
                    sub_urls[dataset], output=str(save_dir), quiet=False, remaining_ok=True
                )
                return
            raise RuntimeError(f"Invalid dataset {dataset}")

        if self.dataset == "synthetic-all":
            for dataset in urls["inputs-processed"].keys():
                if 'synthetic-' in dataset:
                    download_dataset(dataset)
        elif self.dataset == "processed-all":
            for dataset in urls["inputs-processed"].keys():
                download_dataset(dataset)
        elif self.dataset == "raw-all":
            for dataset in urls["inputs-raw"].keys():
                download_dataset(dataset)
        else:
            download_dataset(self.dataset)

if __name__ == "__main__":
    tyro.cli(DownloadProcessedData).main()