import logging
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from process_sai_custom import DEFAULT_OUT_FOLDER

# Global executor for cleanup
executor = None


def signal_handler(signum, frame):
    """Handle termination signals by cleaning up the executor"""
    global executor
    if executor:
        main_logger.info("Received termination signal. Shutting down gracefully...")
        executor.shutdown(wait=False, cancel_futures=True)
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

MONITORED_PATH = os.environ.get("MONITORED_PATH", "~/origin/origin")
PROCESSING_PATH = os.environ.get("PROCESSING_PATH", "~/origin/processing")
PROCESSED_PATH = os.environ.get("PROCESSED_PATH", "~/origin/processed")

MAIN_LOG_FILE = os.environ.get("MAIN_LOG_FILE")
JOB_LOG_DIR = os.environ.get("JOB_LOG_DIR")
MAIN_LOGGER_PREFIX = os.environ.get("MAIN_LOGGER_PREFIX", "[MAIN]")
JOB_LOGGER_PREFIX = os.environ.get("JOB_LOGGER_PREFIX", "[JOB]")

SAI_PREVIEW = os.environ.get("SAI_PREVIEW", "OFF")
SKIP_COLMAP = os.environ.get("SKIP_COLMAP", "ON")
MIN_REQUIRED = int(os.environ.get("MIN_REQUIRED_CUDA_MEM", 2500))  # MiB per job

# Convert string 'true'/'false' to boolean
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

os.makedirs(MONITORED_PATH, exist_ok=True)
os.makedirs(PROCESSED_PATH, exist_ok=True)
os.makedirs(PROCESSING_PATH, exist_ok=True)


def setup_logger(name, log_file, level=logging.INFO):
    """Setup a logger that writes to both file and console"""
    prefix = MAIN_LOGGER_PREFIX if name == "main" else JOB_LOGGER_PREFIX
    formatter = logging.Formatter(
        f"%(asctime)s {prefix} [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with rotation (max 10MB per file, keep 5 backup files)
    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setFormatter(formatter)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    # Logger configuration
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


# Setup main logger using the log file from shell script
if MAIN_LOG_FILE:
    Path(MAIN_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    main_logger = setup_logger("main", MAIN_LOG_FILE)
else:
    main_logger = setup_logger("main", "mido_process_train_sai.log")

# Ensure job log directory exists
if JOB_LOG_DIR:
    Path(JOB_LOG_DIR).mkdir(parents=True, exist_ok=True)


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

    # Setup job-specific logger with prefix from shell script
    job_logger = setup_logger(
        f"job_{name}",
        os.path.join(JOB_LOG_DIR, f"{name}.log") if JOB_LOG_DIR else log_file,
    )

    job_logger.info(f"Starting processing and training for {zip_path}")
    try:
        # Redirect stdout and stderr to the logger
        class LoggerWriter:
            def __init__(self, logger, level):
                self.logger = logger
                self.level = level
                self.buf = []

            def write(self, message):
                if message.strip():
                    self.logger.log(self.level, message.strip())

            def flush(self):
                pass

        sys.stdout = LoggerWriter(job_logger, logging.INFO)
        sys.stderr = LoggerWriter(job_logger, logging.ERROR)

        # process_sai_custom.py
        args1 = [zip_path, None]
        if SKIP_COLMAP == "ON":
            args1.append("--skip_colmap")
        if SAI_PREVIEW == "ON":
            args1.append("--preview")
        if DRY_RUN:
            args1.append("--dry_run")

        parsed_args1 = process_sai_custom.parse_process_args(args1)
        process_sai_custom.process(parsed_args1)

        # train.py
        args2 = [f"{DEFAULT_OUT_FOLDER}/{name}", "--no_eval", "--train_all"]
        if SAI_PREVIEW == "ON":
            args2.append("--preview")
        if DRY_RUN:
            args2.append("--dry_run")

        parsed_args2 = train.parse_train_args(args2)
        train.process(parsed_args2.input_folder, parsed_args2)

        # Restore stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        os.rename(zip_path, processed_path)
        job_logger.info(f"Finished processing and training for {zip_path}")
    except Exception as e:
        job_logger.error(f"Error processing {zip_path}: {e}", exc_info=True)
        # Restore stdout and stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


def dry_run():
    zipfiles = [f for f in os.listdir(MONITORED_PATH) if f.endswith(".zip")]

    for zipfile in zipfiles:
        zip_path = os.path.join(MONITORED_PATH, zipfile)
        processing_path = os.path.join(PROCESSING_PATH, zipfile)
        processed_path = os.path.join(PROCESSED_PATH, zipfile)
        name = zipfile[:-4]
        log_file = os.path.join(JOB_LOG_DIR if JOB_LOG_DIR else "logs", f"{name}.log")
        if os.path.exists(processed_path) or os.path.exists(processing_path):
            continue
        os.rename(zip_path, processing_path)
        run_job(processing_path, processed_path, log_file, name)

        main_logger.info(f"Launched job for {zipfile}")
        time.sleep(2)  # Give time for CUDA memory to update


def main():
    global executor

    # In dry run mode, we don't need a process pool
    if DRY_RUN:
        main_logger.info("DRY RUN: Would monitor for zip files and process them")
        main_logger.info(f"DRY RUN: Would watch directory: {MONITORED_PATH}")
        dry_run()
        return

    executor = ProcessPoolExecutor()
    try:
        futures = []
        running_jobs = 0
        while True:
            # Process any completed futures and remove them
            done_futures = [f for f in futures if f.done()]
            for future in done_futures:
                try:
                    # Get the result to ensure any exceptions are raised
                    future.result()
                except Exception as e:
                    main_logger.error(f"Job failed: {e}", exc_info=True)
                futures.remove(future)

            launched = False
            zipfiles = [f for f in os.listdir(MONITORED_PATH) if f.endswith(".zip")]
            for zipfile in zipfiles:
                zip_path = os.path.join(MONITORED_PATH, zipfile)
                processing_path = os.path.join(PROCESSING_PATH, zipfile)
                processed_path = os.path.join(PROCESSED_PATH, zipfile)
                name = zipfile[:-4]
                log_file = os.path.join(
                    JOB_LOG_DIR if JOB_LOG_DIR else "logs", f"{name}.log"
                )
                if os.path.exists(processed_path) or os.path.exists(processing_path):
                    continue

                running_jobs = len([f for f in futures if not f.done()])
                cuda_free = get_free_cuda_memory()
                required_mem = (running_jobs + 1) * MIN_REQUIRED

                if cuda_free >= required_mem:
                    os.rename(zip_path, processing_path)
                    future = executor.submit(
                        run_job, processing_path, processed_path, log_file, name
                    )
                    futures.append(future)
                    launched = True
                    main_logger.info(f"Launched job for {zipfile}")
                    time.sleep(2)  # Give time for CUDA memory to update
                else:
                    main_logger.warning(
                        f"Skipping {zip_path}: Not enough free CUDA memory "
                        f"({cuda_free} MiB, need at least {required_mem} MiB "
                        f"for {running_jobs+1} jobs)"
                    )

            if not launched:
                main_logger.info("No jobs launched. Sleeping for 5 minutes.")
                time.sleep(300)

    except KeyboardInterrupt:
        main_logger.info("Received interrupt, shutting down...")

    finally:
        # Clean up executor and any running processes
        if executor:
            main_logger.info("Shutting down executor and cleaning up processes...")
            executor.shutdown(wait=False, cancel_futures=True)
            executor = None


if __name__ == "__main__":
    main()
