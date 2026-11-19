#!/usr/bin/env python3
"""
continuous_runner.py: Runner continuous archival untuk merangkum seluruh katalog video Pecah Telur.
Mendukung pause/resume otomatis, checkpointing berkala, dan auto-push ke GitHub.
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from fetch_catalog import fetch_catalog, CATALOG_FILE
from extract_subtitles import extract_subtitle
from summarize_llm import summarize_video
from generate_moc import build_moc, parse_frontmatter
from run_pipeline import git_checkpoint, get_existing_processed_ids

VAULT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR = VAULT_DIR / "Kisah-Sukses"
DATA_DIR = VAULT_DIR / "data"
PROGRESS_FILE = DATA_DIR / "archival_progress.json"

running = True

def handle_sigint(sig, frame):
    global running
    print("\n[INFO] Menerima sinyal stop. Menyelesaikan video yang sedang berjalan sebelum keluar...")
    running = False

signal.signal(signal.SIGINT, handle_sigint)
signal.signal(signal.SIGTERM, handle_sigint)

def update_progress_status(current_idx, total_targets, total_catalog, success_count, fail_count, current_video_title=""):
    existing = len(get_existing_processed_ids())
    pct = (existing / total_catalog * 100) if total_catalog else 0
    status = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_catalog": total_catalog,
        "total_completed_vault": existing,
        "completion_percentage": round(pct, 2),
        "batch_attempted": current_idx,
        "batch_success": success_count,
        "batch_failed": fail_count,
        "current_video": current_video_title,
        "status": "RUNNING" if running else "STOPPED"
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def run_archival(batch_limit=100, checkpoint_interval=10, auto_push=True):
    global running
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
    
    if not CATALOG_FILE.exists():
        print("[INFO] Mengambil katalog video penuh channel...")
        videos = fetch_catalog(limit=1200)
    else:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            videos = json.load(f)

    existing_ids = get_existing_processed_ids()
    total_catalog = len(videos)
    print(f"📊 [ARCHIVAL STATUS] Total Katalog: {total_catalog} video | Sudah dirangkum: {len(existing_ids)} video ({len(existing_ids)/total_catalog*100:.1f}%)")

    # Queue unprocessed videos
    unprocessed = [v for v in videos if v["id"] not in existing_ids]
    print(f"🎯 Antrean belum diproses: {len(unprocessed)} video")

    if not unprocessed:
        print("🎉 Luar biasa! Seluruh 100% video di channel Pecah Telur sudah selesai dirangkum!")
        return

    targets = unprocessed[:batch_limit] if batch_limit else unprocessed
    print(f"🚀 Memulai pemrosesan batch sebesar {len(targets)} video (Checkpoint tiap {checkpoint_interval} video)...")
    print("=" * 65)

    success_count = 0
    fail_count = 0

    start_time = time.time()

    for idx, video in enumerate(targets, 1):
        if not running:
            print("\n[STOP] Runner dihentikan dengan aman.")
            break

        vid = video["id"]
        title = video.get("title", vid)
        print(f"\n[{idx}/{len(targets)}] (Total Vault: {len(existing_ids) + success_count + 1}/{total_catalog}) 🎬 [{vid}] {title[:60]}...")
        update_progress_status(idx, len(targets), total_catalog, success_count, fail_count, title)

        try:
            # Step 1: Subtitle
            vtt_path = extract_subtitle(vid)
            if not vtt_path or not vtt_path.exists():
                print(f"[SKIP] Subtitle tidak tersedia untuk {vid}")
                fail_count += 1
                continue

            # Step 2: LLM Summarization
            md_path = summarize_video(video, vtt_path)
            if md_path and md_path.exists():
                print(f"[OK] ✓ Tersimpan: {md_path.name}")
                success_count += 1
            else:
                print(f"[FAIL] ✗ Gagal merangkum {vid}")
                fail_count += 1

        except Exception as e:
            print(f"[ERROR-GRACEFUL] Error pada {vid}: {e}. Melanjutkan...")
            fail_count += 1

        # Checkpointing
        if success_count > 0 and success_count % checkpoint_interval == 0:
            print(f"\n🔄 [CHECKPOINT] Memperbarui MOC & Kategori setelah {success_count} video berhasil...")
            build_moc()
            if auto_push:
                git_checkpoint(f"feat: sync {success_count} video summaries to archival vault (total {len(existing_ids) + success_count}/{total_catalog})")

        # Pacing
        time.sleep(2.5)

    # Final wrap-up
    print("\n" + "=" * 65)
    print("🔄 Menyelesaikan pembaruan akhir Master Map of Content (00 - Index Pecah Telur.md)...")
    build_moc()

    if auto_push and success_count > 0:
        print("\n🚀 Melakukan push final batch ke remote GitHub...")
        total_now = len(get_existing_processed_ids())
        git_checkpoint(f"feat: archival batch complete, {total_now}/{total_catalog} videos ({total_now/total_catalog*100:.1f}%)")

    elapsed_mins = (time.time() - start_time) / 60
    print("\n" + "=" * 65)
    print(f"🎉 Batch Archival Selesai dalam {elapsed_mins:.1f} menit!")
    print(f"✅ Berhasil dalam batch ini: {success_count}")
    print(f"⚠️ Gagal / Tanpa Subtitle: {fail_count}")
    print(f"📊 Total Video di Vault Sekarang: {len(get_existing_processed_ids())} / {total_catalog}")
    print(f"📁 Lokasi Vault: {VAULT_DIR}")
    print(f"🌐 GitHub: https://github.com/arifrhm/ringkasan-pecah-telur-channel")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pecah Telur Continuous Archival Runner")
    parser.add_argument("--batch", type=int, default=100, help="Jumlah video yang diproses dalam putaran ini (0 = tanpa henti sampai habis)")
    parser.add_argument("--checkpoint", type=int, default=10, help="Interval checkpoint update MOC dan Git push")
    parser.add_argument("--no-push", action="store_true", help="Nonaktifkan auto push ke GitHub")
    args = parser.parse_args()

    run_archival(
        batch_limit=args.batch if args.batch > 0 else None,
        checkpoint_interval=args.checkpoint,
        auto_push=not args.no_push
    )
