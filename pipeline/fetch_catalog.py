#!/usr/bin/env python3
"""
fetch_catalog.py: Mengambil daftar video dari channel @PecahTelur menggunakan yt-dlp.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOG_FILE = DATA_DIR / "videos_catalog.json"

def fetch_catalog(limit=None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings"
    ]
    if limit:
        cmd.extend(["--playlist-end", str(limit)])
    
    cmd.append("https://www.youtube.com/@PecahTelur/videos")

    print(f"[INFO] Mengambil katalog video (limit={limit or 'SEMUA'})...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    videos = []
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            videos.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "duration": item.get("duration"),
                "duration_string": item.get("duration_string"),
                "view_count": item.get("view_count"),
                "url": item.get("url") or f"https://www.youtube.com/watch?v={item.get('id')}"
            })
            if limit and len(videos) >= limit:
                break
        except json.JSONDecodeError:
            continue

    process.kill()

    # Load existing to merge if needed
    existing = {}
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                for v in json.load(f):
                    existing[v["id"]] = v
        except Exception:
            pass

    for v in videos:
        existing[v["id"]] = v

    merged_list = list(existing.values())
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_list, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Tersimpan {len(merged_list)} video dalam {CATALOG_FILE}")
    return videos

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    fetch_catalog(limit)
