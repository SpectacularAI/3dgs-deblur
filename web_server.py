import importlib.util
import os
import sys
import threading

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel


# Import COS SDK demo logic
def download_from_cos(bucket: str, key: str, local_path: str):
    # Dynamically import cos-sdk-demo.py as a module
    import importlib.util

    spec = importlib.util.spec_from_file_location("cos_sdk_demo", "cos-sdk-demo.py")
    if spec is None or spec.loader is None:
        raise ImportError("Could not load cos-sdk-demo.py module spec or loader.")
    cos_sdk_demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cos_sdk_demo)
    # Use the download_file function from the demo (assume it exists)
    cos_sdk_demo.download_file(bucket, key, local_path)


# Import monitor logic from mido_process_train_sai.py
def start_monitor():
    import mido_process_train_sai

    mido_process_train_sai.main()


MONITORED_PATH = os.environ.get("MONITORED_PATH", "data/origin")

app = FastAPI()


class DownloadRequest(BaseModel):
    bucket: str
    key: str
    filename: str


@app.on_event("startup")
def launch_monitor():
    t = threading.Thread(target=start_monitor, daemon=True)
    t.start()


@app.post("/download")
def download_zip(req: DownloadRequest):
    local_path = os.path.join(MONITORED_PATH, req.filename)
    try:
        download_from_cos(req.bucket, req.key, local_path)
        return {"status": "success", "path": local_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)
