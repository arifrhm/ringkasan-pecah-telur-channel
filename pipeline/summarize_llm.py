#!/usr/bin/env python3
"""
summarize_llm.py: Merangkum transcript YouTube menjadi catatan Obsidian ber-timestamp menggunakan 9Router LLM.
"""

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
import requests

from parse_transcript import parse_vtt, format_transcript_for_prompt

VAULT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = VAULT_DIR / "Kisah-Sukses"
TRANSCRIPTS_DIR = VAULT_DIR / "data" / "transcripts"
DB_PATH = Path("/root/.9router/db/data.sqlite")

def get_9router_api_key():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database 9Router tidak ditemukan di {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT key FROM apiKeys LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        raise ValueError("API key tidak ditemukan di 9Router database")
    return row[0]

SYSTEM_PROMPT = """Anda adalah asisten ahli dokumentasi bisnis dan kurator kisah sukses entrepreneur Indonesia.
Tugas Anda adalah menganalisis transkrip wawancara video channel YouTube "Pecah Telur" dan menyusun ringkasan kisah sukses yang sangat terstruktur, mendalam, dan kaya hikmah bisnis.

PENTING:
- Pastikan informasi tokoh, nama usaha, kategori, lokasi, omzet, dan modal diambil seakurat mungkin dari percakapan.
- Pada bagian "timeline_pernyataan", pilihlah 5 sampai 10 momen/pernyataan paling krusial (turning point, wejangan bisnis, cara menghadapi masalah, modal awal, filosofi hidup).
- 'detik' HARUS berupa integer angka detik yang persis sesuai dengan penanda waktu di transkrip (misal: penanda [01:25] (detik 85) -> detik: 85, waktu: "01:25").
- Respon WAJIB berupa JSON murni tanpa pembuka/penutup markdown ```json (hanya objek JSON).

Format JSON yang diharapkan:
{
  "tokoh": "Nama narasumber/pendiri",
  "nama_bisnis": "Nama brand / usaha",
  "kategori": "Kategori industri (misal: Kuliner, Agribisnis, Peternakan, Retail, Manufaktur, Jasa, dll)",
  "lokasi": "Kota/Kabupaten, Provinsi (misal: Kediri, Jawa Timur)",
  "modal_awal": "Informasi modal awal (atau 'Modal kecil / minim' jika tidak ada angka pasti)",
  "omzet_tertinggi": "Omzet / skala produksi tertinggi yang disebut",
  "golden_quote": "Satu kutipan paling menginspirasi dari narasumber",
  "ringkasan_eksekutif": "2-3 paragraf ringkasan mendalam tentang kisah sukses, latar belakang masalah, dan pencapaiannya",
  "profil_bisnis": [
    "Poin profil 1...",
    "Poin profil 2..."
  ],
  "titik_terendah": [
    "Masa sulit 1...",
    "Titik balik / turning point..."
  ],
  "kunci_sukses": [
    {"strategi": "Nama Strategi", "penjelasan": "Penjelasan detail..."},
    {"strategi": "Nama Strategi", "penjelasan": "Penjelasan detail..."}
  ],
  "timeline_pernyataan": [
    {
      "detik": 48,
      "waktu": "00:48",
      "topik": "Asal Usul & Latar Belakang",
      "kutipan": "Perkataan langsung narasumber..."
    }
  ]
}
"""

def summarize_video(video_meta, vtt_path):
    video_id = video_meta["id"]
    video_title = video_meta["title"]
    duration_str = video_meta.get("duration_string", "")
    youtube_url = video_meta.get("url") or f"https://www.youtube.com/watch?v={video_id}"

    blocks = parse_vtt(vtt_path)
    if not blocks:
        print(f"[ERROR] Transkrip kosong untuk {video_id}")
        return None

    transcript_text = format_transcript_for_prompt(blocks)
    
    # Truncate if ultra long (e.g. > 15000 tokens)
    if len(transcript_text) > 80000:
        transcript_text = transcript_text[:80000] + "\n...[transkrip dipotong karena batas panjang]..."

    user_prompt = f"""Judul Video: {video_title}
URL Video: {youtube_url}
Durasi Total: {duration_str}

Berikut adalah transkrip lengkap wawancara beserta penanda detik:
---
{transcript_text}
---

Silakan buat ekstraksi dan ringkasan terstruktur dalam format JSON sesuai instruksi sistem."""

    api_key = get_9router_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "ag/gemini-3.8-flash-medium",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "stream": False
    }

    print(f"[LLM] Mengirim transkrip {video_id} ({len(blocks)} blok teks) ke 9Router...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.post("http://127.0.0.1:20128/v1/chat/completions", headers=headers, json=payload, timeout=90)
            if res.status_code == 200:
                raw_content = res.json()["choices"][0]["message"]["content"].strip()
                # Clean json codeblocks if any
                clean_json = re.sub(r"^```(?:json)?\s*", "", raw_content)
                clean_json = re.sub(r"\s*```$", "", clean_json).strip()
                data = json.loads(clean_json)
                return render_markdown(video_meta, data)
            else:
                print(f"[WARN] 9Router return {res.status_code}: {res.text[:150]}, mencoba lagi...")
                time.sleep(3)
        except Exception as e:
            print(f"[WARN] Error koneksi/parsing pada attempt {attempt+1}: {e}")
            time.sleep(3)

    return None

def sanitize_filename(name):
    # Remove chars invalid for filenames
    clean = re.sub(r'[\\/*?:"<>|]', '', name)
    clean = re.sub(r'\s+', '-', clean).strip('-')
    return clean[:60]

def render_markdown(video_meta, data):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_id = video_meta["id"]
    title = video_meta["title"]
    duration = video_meta.get("duration_string", "")
    url = f"https://www.youtube.com/watch?v={video_id}"

    tokoh = data.get("tokoh", "Narasumber").strip()
    bisnis = data.get("nama_bisnis", "Bisnis").strip()
    kategori = data.get("kategori", "Umum").strip()
    lokasi = data.get("lokasi", "Indonesia").strip()
    modal = data.get("modal_awal", "-").strip()
    omzet = data.get("omzet_tertinggi", "-").strip()
    quote = data.get("golden_quote", "").strip()

    # Create safe filename: e.g. "Ayam-Panggang-Bangi-Kediri.md"
    base_name = f"{sanitize_filename(bisnis)}-{sanitize_filename(tokoh)}"
    if len(base_name) < 5 or base_name == "Bisnis-Narasumber":
        base_name = sanitize_filename(title)
    
    md_filename = f"{base_name}.md"
    file_path = OUTPUT_DIR / md_filename

    # Tags list
    cat_tag = re.sub(r'[^a-zA-Z0-9_-]', '', kategori.lower().replace(" ", "-"))
    city_tag = re.sub(r'[^a-zA-Z0-9_-]', '', lokasi.split(",")[0].lower().replace(" ", "-"))

    lines = [
        "---",
        f'id: "{video_id}"',
        f'title: "{title}"',
        f'tokoh: "{tokoh}"',
        f'nama_bisnis: "{bisnis}"',
        f'kategori: "[[{kategori}]]"',
        f'lokasi: "{lokasi}"',
        f'modal_awal: "{modal}"',
        f'omzet_tertinggi: "{omzet}"',
        f'durasi: "{duration}"',
        f'youtube_url: "{url}"',
        "tags:",
        "  - pecah-telur",
        "  - kisah-sukses",
        f"  - {cat_tag}",
    ]
    if city_tag:
        lines.append(f"  - {city_tag}")
    lines.extend([
        "---",
        "",
        f"# 🏆 [[{bisnis}]] — {tokoh} ({lokasi})",
        "",
    ])

    if quote:
        lines.extend([
            f"> **\"{quote}\"**",
            f"> — *{tokoh}*",
            "",
            "---",
            ""
        ])

    lines.extend([
        "## 📌 Ringkasan Eksekutif",
        data.get("ringkasan_eksekutif", "").strip(),
        "",
        "---",
        "",
        "## 🧭 Profil Bisnis & Tokoh",
        f"- **Nama Narasumber**: {tokoh}",
        f"- **Nama Usaha**: [[{bisnis}]]",
        f"- **Kategori / Industri**: [[{kategori}]]",
        f"- **Lokasi Usaha**: {lokasi}",
        f"- **Estimasi Modal Awal**: {modal}",
        f"- **Pencapaian / Skala Saat Ini**: {omzet}",
        f"- **Tautan Video**: [Tonton di YouTube]({url})",
        "",
        "### Karakteristik & Model Bisnis",
    ])

    for p in data.get("profil_bisnis", []):
        lines.append(f"- {p}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 📉 Titik Terendah & Perjuangan Awal",
    ])
    for t in data.get("titik_terendah", []):
        lines.append(f"- {t}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## 💡 Kunci Sukses & Strategi Bisnis",
    ])
    for s in data.get("kunci_sukses", []):
        if isinstance(s, dict):
            lines.append(f"1. **{s.get('strategi', 'Strategi')}**: {s.get('penjelasan', '')}")
        else:
            lines.append(f"1. {s}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## ⏱️ Timeline Pernyataan Kunci & Durasi Video",
        "Berikut momen penting dan wejangan langsung dari narasumber beserta tautan detik video:",
        "",
        "| Waktu | Topik / Milestone | Kutipan Narasumber |",
        "| :--- | :--- | :--- |"
    ])

    for item in data.get("timeline_pernyataan", []):
        waktu = item.get("waktu", "00:00")
        sec = item.get("detik", 0)
        topik = item.get("topik", "Momen").replace("|", "-")
        kutipan = item.get("kutipan", "").replace("|", "-").replace("\n", " ").strip()
        link_yt = f"https://youtu.be/{video_id}?t={sec}"
        lines.append(f"| [{waktu}]({link_yt}) | **{topik}** | *\"{kutipan}\"* |")

    lines.extend([
        "",
        "---",
        "",
        "## 🔗 Catatan Terkait & Navigasi",
        f"- Kategori: [[{kategori}]]",
        f"- Indeks Utama: [[00 - Index Pecah Telur]]",
        ""
    ])

    content = "\n".join(lines)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[SAVED] Catatan berhasil dibuat: {file_path}")
    return file_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: summarize_llm.py <video_id> <vtt_file>")
        sys.exit(1)
    
    vid = sys.argv[1]
    vtt = Path(sys.argv[2])
    dummy_meta = {"id": vid, "title": f"Video {vid}", "duration_string": "15:00"}
    summarize_video(dummy_meta, vtt)
