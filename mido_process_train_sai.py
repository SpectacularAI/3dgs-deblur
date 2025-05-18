import importlib
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

LOG_PATH = os.environ.get("LOG_PATH", "data/logs")
MONITORED_PATH = os.environ.get("MONITORED_PATH", "data/origin")
PROCESSING_PATH = os.environ.get("PROCESSING_PATH", "data/origin/processing")
ORIGIN_PROCESSED = os.environ.get("ORIGIN_PROCESSED", "data/origin/processed")
SAI_PREVIEW = os.environ.get("SAI_PREVIEW", "OFF")
SKIP_COLMAP = os.environ.get("SKIP_COLMAP", "ON")
MIN_REQUIRED = 2500  # MiB per job

os.makedirs(ORIGIN_PROCESSED, exist_ok=True)
os.makedirs(PROCESSING_PATH, exist_ok=True)


def get_free_cuda_memory():
    try:
        out = (
            subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.free",
                    "--format=csv,noheader,nounits",
                ]
            )
            .decode()
            .strip()
            .split("\n")[0]
        )
        return int(out)
    except Exception:
        return 0


def run_job(zip_path, processed_path, log_file, name):
    import process_sai_custom
    import train

    with open(log_file, "a") as log:
        log.write(
            f"[{datetime.now()}] Starting processing and training for {zip_path}\n"
        )
        try:
            # process_sai_custom.py
            args1 = [zip_path, None]
            if SKIP_COLMAP == "ON":
                args1.append("--skip_colmap")
            if SAI_PREVIEW == "ON":
                args1.append("--preview")

            parsed_args1 = process_sai_custom.parse_process_args(args1)

            sys.stdout = log
            sys.stderr = log
            process_sai_custom.process(parsed_args1)
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            # train.py
            args2 = [f"data/inputs-processed/custom/{name}", "--no_eval", "--train_all"]
            if SAI_PREVIEW == "ON":
                args2.append("--preview")

            parsed_args2 = train.parse_train_args(args2)
            sys.stdout = log
            sys.stderr = log
            train.process(parsed_args2.input_folder, parsed_args2)
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            os.rename(zip_path, processed_path)
            log.write(
                f"[{datetime.now()}] Finished processing and training for {zip_path}\n"
            )
        except Exception as e:
            log.write(f"[{datetime.now()}] Error processing {zip_path}: {e}\n")


def main():
    with ProcessPoolExecutor() as executor:
        futures = []
        running_jobs = 0
        while True:
            launched = False
            zipfiles = [f for f in os.listdir(MONITORED_PATH) if f.endswith(".zip")]
            for zipfile in zipfiles:
                zip_path = os.path.join(MONITORED_PATH, zipfile)
                processing_path = os.path.join(PROCESSING_PATH, zipfile)
                processed_path = os.path.join(ORIGIN_PROCESSED, zipfile)
                log_file = os.path.join(LOG_PATH, f"{zipfile}.log")
                name = zipfile[:-4]
                if os.path.exists(processed_path) or os.path.exists(processing_path):
                    continue
                # Count running jobs (futures not done)
                running_jobs = sum(1 for f in futures if not f.done())
                cuda_free = get_free_cuda_memory()
                required_mem = (running_jobs + 1) * MIN_REQUIRED
                if cuda_free >= required_mem:
                    os.rename(zip_path, processing_path)
                    future = executor.submit(
                        run_job, processing_path, processed_path, log_file, name
                    )
                    futures.append(future)
                    launched = True
                    time.sleep(2)  # Give time for CUDA memory to update
                else:
                    with open(log_file, "a") as log:
                        log.write(
                            f"[{datetime.now()}] Skipping {zip_path}: Not enough free CUDA memory ({cuda_free} MiB, need at least {required_mem} MiB for {running_jobs+1} jobs). Will check again in 5 minutes.\n"
                        )
            if not launched:
                print(f"[{datetime.now()}] No jobs launched. Sleeping for 5 minutes.\n")
                time.sleep(300)
            # Clean up finished futures
            futures = [f for f in futures if not f.done()]


if __name__ == "__main__":
    main()
