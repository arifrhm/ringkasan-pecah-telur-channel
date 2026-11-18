#!/usr/bin/env python3
"""
run_pipeline.py: Orkestrator utama pipeline ringkasan Pecah Telur (Massive & Graceful).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from fetch_catalog import fetch_catalog, CATALOG_FILE
from extract_subtitles import extract_subtitle
from summarize_llm import summarize_video
from generate_moc import build_moc, parse_frontmatter

VAULT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR = VAULT_DIR / "Kisah-Sukses"
DATA_DIR = VAULT_DIR / "data"

def get_existing_processed_ids():
    processed = set()
    if not STORIES_DIR.exists():
        return processed
    for md_file in STORIES_DIR.glob("*.md"):
        meta = parse_frontmatter(md_file)
        if "id" in meta:
            processed.add(meta["id"])
    return processed

def git_checkpoint(message="chore: periodic vault checkpoint and MOC update"):
    try:
        subprocess.run(["git", "add", "."], cwd=str(VAULT_DIR), check=True)
        # Check if there are changes to commit
        res = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=str(VAULT_DIR))
        if res.returncode != 0:
            subprocess.run(["git", "commit", "-m", message], cwd=str(VAULT_DIR), check=True)
            print("[GIT] Berhasil membuat commit checkpoint lokal.")
            # Push to origin
            push_res = subprocess.run(["git", "push", "origin", "main"], cwd=str(VAULT_DIR), capture_output=True, text=True)
            if push_res.returncode == 0:
                print("[GIT] ✓ Berhasil push checkpoint ke remote GitHub!")
            else:
                print(f"[GIT-WARN] Push belum berhasil: {push_res.stderr.strip()[:150]}")
    except Exception as e:
        print(f"[GIT-WARN] Gagal melakukan checkpoint git: {e}")

def run(limit=20, video_id=None, force=False, auto_push=True, checkpoint_interval=5):
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
            videos = fetch_catalog(limit=max(limit * 2, 50))
        else:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                videos = json.load(f)
            if len(videos) < (len(existing_ids) + limit):
                needed = len(existing_ids) + limit + 20
                print(f"[INFO] Memperbarui katalog untuk memenuhi target ({needed} video)...")
                videos = fetch_catalog(limit=needed)

    # Filter videos to process
    targets = []
    for v in videos:
        vid = v["id"]
        if not force and vid in existing_ids:
            continue
        targets.append(v)

    if not targets:
        print("✅ Seluruh video dalam katalog sudah selesai dirangkum!")
        return

    print(f"\n🚀 Memulai pemrosesan masif untuk {len(targets)} video target (Checkpoint tiap {checkpoint_interval} video)...")
    print("=" * 65)

    success_count = 0
    fail_count = 0
    skipped_list = []

    for idx, video in enumerate(targets, 1):
        vid = video["id"]
        title = video.get("title", vid)
        print(f"\n[{idx}/{len(targets)}] 🎬 [{vid}] {title}")

        try:
            # Step A: Unduh Subtitle
            vtt_path = extract_subtitle(vid)
            if not vtt_path or not vtt_path.exists():
                print(f"[SKIP] Dilewati: Subtitle tidak tersedia untuk {vid}")
                fail_count += 1
                skipped_list.append({"id": vid, "title": title, "reason": "No subtitle"})
                continue

            # Step B: LLM Summarization
            md_path = summarize_video(video, vtt_path)
            if md_path and md_path.exists():
                print(f"[OK] ✓ Catatan berhasil: {md_path.name}")
                success_count += 1
                if success_count >= limit:
                    print(f"\n🎯 Target {limit} video sukses telah tercapai!")
                    break
            else:
                print(f"[FAIL] ✗ Gagal merangkum {vid}")
                fail_count += 1
                skipped_list.append({"id": vid, "title": title, "reason": "LLM summarize failed"})

        except Exception as e:
            print(f"[ERROR-GRACEFUL] Error tak terduga pada {vid}: {e}. Melanjutkan ke video berikutnya...")
            fail_count += 1
            skipped_list.append({"id": vid, "title": title, "reason": str(e)})

        # Periodic Checkpointing & MOC update
        if success_count > 0 and success_count % checkpoint_interval == 0:
            print(f"\n🔄 [CHECKPOINT] Memperbarui MOC setelah {success_count} video berhasil...")
            build_moc()
            if auto_push:
                git_checkpoint(f"feat: sync {success_count} video summaries and update MOC")

        # Pacing antar video agar tetap graceful
        time.sleep(2.5)

    # Final Step: Rebuild MOC Index
    print("\n" + "=" * 65)
    print("🔄 Memperbarui Master Map of Content (00 - Index Pecah Telur.md)...")
    build_moc()

    # Final Git Sync
    if auto_push and success_count > 0:
        print("\n🚀 Melakukan push final ke GitHub...")
        git_checkpoint(f"feat: add batch of {success_count} video summaries to Obsidian vault")

    # Save summary log
    status_summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_attempted": len(targets),
        "success": success_count,
        "failed": fail_count,
        "skipped_details": skipped_list
    }
    with open(DATA_DIR / "last_batch_status.json", "w", encoding="utf-8") as f:
        json.dump(status_summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(f"🎉 Batch Masif Selesai! Berhasil: {success_count}, Gagal/Dilewati: {fail_count}")
    print(f"📁 Lokasi Vault: {VAULT_DIR}")
    print(f"🌐 GitHub: https://github.com/arifrhm/ringkasan-pecah-telur-channel")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orkestrator Ringkasan Kisah Sukses Pecah Telur")
    parser.add_argument("--limit", type=int, default=15, help="Jumlah video yang diproses dalam batch")
    parser.add_argument("--video-id", type=str, default=None, help="Proses 1 video spesifik berdasarkan ID")
    parser.add_argument("--force", action="store_true", help="Proses ulang video meskipun sudah ada catatannya")
    parser.add_argument("--no-push", action="store_true", help="Nonaktifkan auto push ke GitHub")
    parser.add_argument("--checkpoint", type=int, default=5, help="Interval checkpoint update MOC dan Git")
    args = parser.parse_args()

    run(
        limit=args.limit,
        video_id=args.video_id,
        force=args.force,
        auto_push=not args.no_push,
        checkpoint_interval=args.checkpoint
    )
