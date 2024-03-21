"""Script to download processed datasets."""
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import tyro


@dataclass
class DownloadProcessedData:
    save_dir: Path = Path(os.getcwd() + "/data")
    """Save directory. Default /data."""
    dataset: Literal["synthetic", "sai"] = "synthetic"
    """Dataset download name. Set to 'synthetic' to download all synthetic data. Set to 'spectacular' for real world smartphone captures."""

    def main(self):
        self.save_dir.mkdir(parents=True, exist_ok=True)

        urls = {
            "inputs-processed": {
                "synthetic-all": "https://zenodo.org/records/10847884/files/processed-nerfstudio.zip",
                "colmap-sai-cli-orig-intrinsics-blur-scored": "https://zenodo.org/records/10848124/files/colmap-sai-cli-orig-intrinsics-blur-scored.tar.xz",
                "colmap-sai-cli-calib-intrinsics-blur-scored": "https://zenodo.org/records/10848124/files/colmap-sai-cli-calib-intrinsics-blur-scored.tar.xz",
                "colmap-sai-cli-vels-blur-scored.zip": "https://zenodo.org/records/10848124/files/colmap-sai-cli-vels-blur-scored.zip",
            }
        }

        def download_dataset(dataset):
            for subfolder, sub_urls in urls.items():
                save_dir = self.save_dir / subfolder
                save_dir.mkdir(parents=True, exist_ok=True)
                download_command = ["wget", "-P", str(self.save_dir), sub_urls[dataset]]

                # download
                try:
                    subprocess.run(download_command, check=True)
                    print("File file downloaded succesfully.")
                except subprocess.CalledProcessError as e:
                    print(f"Error downloading file: {e}")

                file_name = Path(sub_urls[dataset]).name

                # subsubfolder for sai data
                subsubfolder = file_name.split(".")[0] if "sai" in file_name else ""
                if subsubfolder:
                    Path(self.save_dir / subfolder / subsubfolder).mkdir(
                        parents=True, exist_ok=True
                    )

                # deal with zip or tar formats
                if Path(sub_urls[dataset]).suffix == ".zip":
                    extract_command = [
                        "unzip",
                        self.save_dir / file_name,
                        "-d",
                        self.save_dir / Path(subfolder) / subsubfolder,
                    ]
                else:
                    extract_command = [
                        "tar",
                        "-xvJf",
                        self.save_dir / file_name,
                        "-C",
                        self.save_dir / Path(subfolder) / subsubfolder,
                    ]

                # extract
                try:
                    subprocess.run(extract_command, check=True)
                    print("Extraction complete.")
                except subprocess.CalledProcessError as e:
                    print(f"Extraction failed: {e}")

        if self.dataset == "synthetic":
            for dataset in urls["inputs-processed"].keys():
                if "synthetic" in dataset:
                    download_dataset(dataset)
        elif self.dataset == "sai":
            for dataset in urls["inputs-processed"].keys():
                if "sai" in dataset:
                    download_dataset(dataset)
        else:
            raise NotImplementedError


if __name__ == "__main__":
    tyro.cli(DownloadProcessedData).main()
