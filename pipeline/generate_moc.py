#!/usr/bin/env python3
"""
generate_moc.py: Membangun Master Map of Content (00 - Index Pecah Telur.md) dan halaman Kategori.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

VAULT_DIR = Path(__file__).resolve().parent.parent
STORIES_DIR = VAULT_DIR / "Kisah-Sukses"
CATEGORIES_DIR = VAULT_DIR / "Kategori"
MOC_FILE = VAULT_DIR / "00 - Index Pecah Telur.md"

def parse_frontmatter(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    raw_yaml = match.group(1)
    meta = {}
    for line in raw_yaml.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Strip wikilink brackets if present in frontmatter value
            val_clean = re.sub(r"\[\[(.*?)\]\]", r"\1", val)
            meta[key] = val_clean

    meta["filename"] = file_path.stem
    return meta

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', '-', name)
    clean = re.sub(r'\s+', ' ', clean).strip(' -')
    return clean

def build_moc():
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(list(STORIES_DIR.glob("*.md")))
    print(f"[MOC] Menemukan {len(md_files)} catatan kisah sukses...")

    entries = []
    by_category = defaultdict(list)
    by_location = defaultdict(list)

    for f in md_files:
        meta = parse_frontmatter(f)
        if not meta:
            continue
        entries.append(meta)
        cat = meta.get("kategori", "Lainnya") or "Lainnya"
        by_category[cat].append(meta)
        loc = meta.get("lokasi", "Indonesia") or "Indonesia"
        by_location[loc].append(meta)

    # 1. Generate MOC File
    moc_lines = [
        "---",
        'title: "Index Kisah Sukses Channel Pecah Telur"',
        'type: "moc"',
        f'total_video: {len(entries)}',
        "tags:",
        "  - pecah-telur",
        "  - moc",
        "  - index",
        "---",
        "",
        "# 🍳 Peta Indeks Kisah Sukses Channel Pecah Telur",
        "",
        "> Kumpulan ringkasan terstruktur, strategi bisnis, dan milestone penting ber-timestamp dari wawancara wirausahawan inspiratif di channel YouTube **[Pecah Telur](https://www.youtube.com/@PecahTelur)**.",
        "",
        f"📊 **Statistik**: Total `{len(entries)}` Video Terangkum | Terindeks dalam format Obsidian Vault.",
        "",
        "---",
        "",
        "## 📁 Indeks Berdasarkan Kategori Industri",
        ""
    ]

    for cat, items in sorted(by_category.items()):
        safe_cat_name = sanitize_filename(cat)
        cat_wikilink = f"[[{safe_cat_name}|{cat}]]" if safe_cat_name != cat else f"[[{cat}]]"
        moc_lines.append(f"### 🏷️ {cat_wikilink} ({len(items)} Video)")
        for item in items:
            note_link = f"[[{item['filename']}|{item.get('nama_bisnis', item['filename'])}]]"
            tokoh = item.get("tokoh", "Narasumber")
            lokasi = item.get("lokasi", "-")
            moc_lines.append(f"- {note_link} — *{tokoh}* ({lokasi})")
        moc_lines.append("")

    moc_lines.extend([
        "---",
        "",
        "## 🗺️ Indeks Berdasarkan Wilayah",
        ""
    ])

    for loc, items in sorted(by_location.items()):
        moc_lines.append(f"- **{loc}** ({len(items)} usaha): " + ", ".join([f"[[{i['filename']}|{i.get('nama_bisnis', i['filename'])}]]" for i in items]))

    moc_lines.extend([
        "",
        "---",
        "",
        "## 📋 Master Tabel Semua Kisah Sukses",
        "",
        "| No | Bisnis & Catatan Obsidian | Tokoh | Kategori | Lokasi | Pencapaian / Omzet | Video |",
        "| :---: | :--- | :--- | :--- | :--- | :--- | :---: |"
    ])

    for idx, item in enumerate(entries, 1):
        note_link = f"[[{item['filename']}|{item.get('nama_bisnis', item['filename'])}]]"
        tokoh = item.get("tokoh", "-")
        raw_cat = item.get('kategori', 'Umum')
        safe_cat = sanitize_filename(raw_cat)
        cat_link = f"[[{safe_cat}|{raw_cat}]]" if safe_cat != raw_cat else f"[[{raw_cat}]]"
        lokasi = item.get("lokasi", "-")
        omzet = item.get("omzet_tertinggi", "-")
        yt_url = item.get("youtube_url", "#")
        moc_lines.append(f"| {idx} | {note_link} | {tokoh} | {cat_link} | {lokasi} | {omzet} | [YouTube]({yt_url}) |")

    moc_lines.append("")
    with open(MOC_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(moc_lines))
    print(f"[SUCCESS] Master MOC berhasil ditulis: {MOC_FILE}")

    # 2. Generate Individual Category Pages in Kategori/
    for cat, items in by_category.items():
        safe_cat_name = sanitize_filename(cat)
        cat_file = CATEGORIES_DIR / f"{safe_cat_name}.md"
        cat_lines = [
            "---",
            f'title: "Kategori Bisnis: {cat}"',
            f'kategori: "{cat}"',
            f'jumlah_usaha: {len(items)}',
            "tags:",
            "  - kategori-bisnis",
            "  - pecah-telur",
            "---",
            "",
            f"# 🏷️ Kategori: {cat}",
            "",
            f"Daftar wawancara wirausahawan di channel Pecah Telur dalam bidang **{cat}**:",
            "",
            "| Bisnis | Tokoh | Lokasi | Omzet / Skala | Catatan Obsidian |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]
        for it in items:
            cat_lines.append(f"| **{it.get('nama_bisnis', '-')}** | {it.get('tokoh', '-')} | {it.get('lokasi', '-')} | {it.get('omzet_tertinggi', '-')} | [[{it['filename']}]] |")
        
        cat_lines.extend([
            "",
            "---",
            "Kembali ke: [[00 - Index Pecah Telur]]",
            ""
        ])
        with open(cat_file, "w", encoding="utf-8") as f:
            f.write("\n".join(cat_lines))

    print(f"[SUCCESS] Diperbarui {len(by_category)} halaman kategori di {CATEGORIES_DIR}")

if __name__ == "__main__":
    build_moc()
