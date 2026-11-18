#!/usr/bin/env python3
"""
extract_subtitles.py: Mengunduh automatic subtitle bahasa Indonesia dari video YouTube.
"""

import os
import subprocess
import sys
from pathlib import Path

TRANSCRIPTS_DIR = Path(__file__).resolve().parent.parent / "data" / "transcripts"

def extract_subtitle(video_id):
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    target_vtt = TRANSCRIPTS_DIR / f"{video_id}.id.vtt"
    
    if target_vtt.exists() and target_vtt.stat().st_size > 500:
        print(f"[CACHE] Subtitle untuk {video_id} sudah ada: {target_vtt.name}")
        return target_vtt

    print(f"[DOWNLOAD] Mengunduh subtitle Bahasa Indonesia untuk {video_id}...")
    output_template = str(TRANSCRIPTS_DIR / f"{video_id}.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "id",
        "--sub-format", "vtt",
        "--skip-download",
        "--no-warnings",
        "-o", output_template,
        f"https://www.youtube.com/watch?v={video_id}"
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if target_vtt.exists() and target_vtt.stat().st_size > 100:
        print(f"[SUCCESS] Subtitle tersimpan: {target_vtt.name}")
        return target_vtt
    else:
        print(f"[WARN] Gagal mendapatkan subtitle bahasa Indonesia untuk {video_id}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_subtitles.py <video_id>")
        sys.exit(1)
    extract_subtitle(sys.argv[1])
