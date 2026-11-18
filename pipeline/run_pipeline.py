#!/usr/bin/env python3
"""
run_pipeline.py: Orkestrator utama pipeline ringkasan Pecah Telur.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from fetch_catalog import fetch_catalog, CATALOG_FILE
from extract_subtitles import extract_subtitle
from summarize_llm import summarize_video
from generate_moc import build_moc, parse_frontmatter

VAULT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR = VAULT_DIR / "Kisah-Sukses"

def get_existing_processed_ids():
    processed = set()
    if not STORIES_DIR.exists():
        return processed
    for md_file in STORIES_DIR.glob("*.md"):
        meta = parse_frontmatter(md_file)
        if "id" in meta:
            processed.add(meta["id"])
    return processed

def run(limit=5, video_id=None, force=False):
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
    existing_ids = get_existing_processed_ids()
    print(f"[STATUS] Ditemukan {len(existing_ids)} video yang sudah dirangkum sebelumnya.")

    # 1. Video Selection
    if video_id:
        videos = [{
            "id": video_id,
            "title": f"Video {video_id}",
            "duration_string": "-",
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }]
    else:
        # Load or fetch catalog
        if not CATALOG_FILE.exists():
            print("[INFO] Katalog belum ada, mengambil katalog dari channel...")
            videos = fetch_catalog(limit=max(limit * 2, 20))
        else:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                videos = json.load(f)
            if len(videos) < limit:
                print(f"[INFO] Memperbarui katalog untuk memenuhi limit={limit}...")
                videos = fetch_catalog(limit=limit)

    # Filter videos to process
    targets = []
    for v in videos:
        vid = v["id"]
        if not force and vid in existing_ids:
            continue
        targets.append(v)
        if len(targets) >= limit:
            break

    print(f"\n🚀 Memulai proses untuk {len(targets)} video target...\n" + "="*50)

    success_count = 0
    fail_count = 0

    for idx, video in enumerate(targets, 1):
        vid = video["id"]
        title = video.get("title", vid)
        print(f"\n[{idx}/{len(targets)}] 🎬 Memproses: {title} ({vid})")

        # Step A: Unduh Subtitle
        vtt_path = extract_subtitle(vid)
        if not vtt_path or not vtt_path.exists():
            print(f"[SKIP] Dilewati karena subtitle tidak tersedia untuk {vid}")
            fail_count += 1
            continue

        # Step B: LLM Summarization
        md_path = summarize_video(video, vtt_path)
        if md_path and md_path.exists():
            print(f"[OK] Selesai dirangkum: {md_path.name}")
            success_count += 1
        else:
            print(f"[FAIL] Gagal merangkum {vid}")
            fail_count += 1

        # Pacing
        time.sleep(2)

    # Step C: Rebuild MOC Index
    print("\n" + "="*50)
    print("🔄 Memperbarui Master Map of Content (00 - Index Pecah Telur.md)...")
    build_moc()

    print("\n" + "="*50)
    print(f"🎉 Pipeline selesai! Berhasil: {success_count}, Gagal/Dilewati: {fail_count}")
    print(f"📁 Lokasi Vault: {VAULT_DIR}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orkestrator Ringkasan Kisah Sukses Pecah Telur")
    parser.add_argument("--limit", type=int, default=5, help="Jumlah video yang diproses dalam batch")
    parser.add_argument("--video-id", type=str, default=None, help="Proses 1 video spesifik berdasarkan ID")
    parser.add_argument("--force", action="store_true", help="Proses ulang video meskipun sudah ada catatannya")
    args = parser.parse_args()

    run(limit=args.limit, video_id=args.video_id, force=args.force)
