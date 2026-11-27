import os
import uuid
import zipfile
import subprocess
from pathlib import Path

import whisper
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ClipForge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path("/tmp/clipforge")
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"

UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")

model = None


def get_model():
    global model
    if model is None:
        model = whisper.load_model("tiny")
    return model


@app.get("/health")
def health():
    return {"status": "ClipForge is running!"}


@app.post("/api/process")
async def process_video(
    file: UploadFile = File(...),
    clip_length: int = Form(30),
    clip_count: int = Form(3),
):
    if not file.filename.lower().endswith(
        (".mp4", ".mov", ".mkv", ".webm")
    ):
        raise HTTPException(400, "Please upload a video file.")

    if clip_length not in [15, 20, 30, 45, 60]:
        raise HTTPException(400, "Invalid clip length.")

    if clip_count not in [3, 5, 10]:
        raise HTTPException(400, "Invalid clip count.")

    job_id = str(uuid.uuid4())
    video_path = UPLOADS / f"{job_id}.mp4"
    job_folder = OUTPUTS / job_id
    job_folder.mkdir(parents=True, exist_ok=True)

    try:
        with open(video_path, "wb") as f:
            f.write(await file.read())

        result = get_model().transcribe(
            str(video_path),
            fp16=False,
            verbose=False
        )

        segments = result.get("segments", [])

        if not segments:
            raise HTTPException(400, "No speech was detected.")

        scored = []

        for segment in segments:
            text = segment.get("text", "").strip()
            duration = segment["end"] - segment["start"]
            words = len(text.split())

            if duration > 0 and words >= 3:
                score = words / duration
                scored.append((score, segment))

        if not scored:
            raise HTTPException(400, "Couldn't find suitable moments.")

        scored.sort(key=lambda item: item[0], reverse=True)

        video_info = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ])

        video_duration = float(video_info.decode().strip())
        selected = []

        for score, segment in scored:
            middle = (segment["start"] + segment["end"]) / 2
            start = max(0, middle - clip_length / 2)
            end = min(video_duration, start + clip_length)
            start = max(0, end - clip_length)

            if end - start < 5:
                continue

            if all(
                abs(start - existing[0]) > clip_length * 0.75
                for existing in selected
            ):
                selected.append((start, end, segment))

            if len(selected) >= clip_count:
                break

        if not selected:
            raise HTTPException(400, "No suitable clips found.")

        clips = []

        for index, (start, end, segment) in enumerate(selected, 1):
            output = job_folder / f"clip_{index}.mp4"
            duration = end - start

            command = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(video_path),
                "-t", str(duration),
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(output)
            ]

            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            clips.append({
                "name": f"Clip {index}",
                "url": f"/outputs/{job_id}/clip_{index}.mp4",
                "text": segment.get("text", "")
            })

        zip_path = job_folder / "clips.zip"

        with zipfile.ZipFile(zip_path, "w") as archive:
            for index in range(1, len(clips) + 1):
                archive.write(
                    job_folder / f"clip_{index}.mp4",
                    f"ClipForge_{index}.mp4"
                )

        return {
            "success": True,
            "clips": clips,
            "zip_url": f"/outputs/{job_id}/clips.zip"
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            500,
            f"Video processing failed: {str(error)}"
        )

@app.get("/")
def home():
    frontend = Path("frontend/index.html")
    return FileResponse(frontend)


app.mount(
    "/",
    StaticFiles(directory="frontend"),
    name="frontend"
)
