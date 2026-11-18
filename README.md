# 🍳 Ringkasan Kisah Sukses Channel Pecah Telur (Obsidian Vault & Knowledge Base)

Dokumentasi terstruktur dan repositori catatan pengetahuan (knowledge base) berisi intisari kisah sukses, strategi bisnis, turning point, dan wejangan wirausahawan inspiratif dari channel YouTube **[Pecah Telur](https://www.youtube.com/@PecahTelur)**.

Catatan ini dirancang khusus untuk dibaca di **[Obsidian](https://obsidian.md/)** dengan fitur interlink Wikilinks (`[[...]]`), metadata Frontmatter YAML, serta tabel kutipan ber-timestamp yang terhubung langsung ke detik video YouTube terkait.

---

## 🌟 Fitur Utama

1. **⏱️ Timeline Ber-Timestamp Langsung ke Detik YouTube**:
   - Setiap wejangan atau pernyataan penting dari narasumber disertai link durasi `[mm:ss](https://youtu.be/<id>?t=<detik>)` yang ketika diklik langsung memutar YouTube di detik pernyataan tersebut diucapkan.
2. **🗂️ Metadata Lengkap Frontmatter YAML**:
   - Terindeks berdasarkan nama tokoh, nama usaha/brand, kategori bisnis, estimasi modal awal, omzet/skala tertinggi, durasi video, dan tag.
3. **🗺️ Master Map of Content (MOC)**:
   - File `00 - Index Pecah Telur.md` yang menyajikan katalog terorganisir berdasarkan:
     - **Kategori Industri** (`[[Kuliner]]`, `[[Agribisnis]]`, `[[Peternakan]]`, `[[Retail & Manufaktur]]`, dll.)
     - **Sebaran Wilayah** (Kediri, Boyolali, Malang, Jogja, dll.)
     - **Master Tabel** pencarian cepat.
4. **🔄 Pipeline Otomatis (yt-dlp + 9Router AI)**:
   - Dilengkapi script otomasi Python untuk mengunduh subtitle resmi/auto-caption, mem-parsing transkrip, melakukan ekstraksi kecerdasan bisnis, dan memperbarui MOC secara otomatis.

---

## 📂 Struktur Direktori Vault

```
ringkasan-pecah-telur-channel/
├── 00 - Index Pecah Telur.md        # Master Map of Content (MOC)
├── README.md                        # Panduan repositori & penggunaan
├── .obsidian/                       # Pengaturan workspace Obsidian
├── Kisah-Sukses/                    # Kumpulan catatan ringkasan per video
│   ├── Ayam-Panggang-Bangi-Bu-Siti.md
│   ├── ...
├── Kategori/                        # Catatan indeks per kategori industri
│   ├── Kuliner.md
│   ├── Peternakan.md
│   └── ...
├── pipeline/                        # Script otomasi ekstraksi & summarization
│   ├── fetch_catalog.py             # Fetch daftar video channel
│   ├── extract_subtitles.py         # Ekstrak auto-subtitles VTT
│   ├── parse_transcript.py          # Parser & pembersih VTT ber-timestamp
│   ├── summarize_llm.py             # LLM Summarizer (via 9Router)
│   ├── generate_moc.py              # Builder Master MOC & halaman kategori
│   └── run_pipeline.py              # Orkestrator CLI
└── data/
    ├── videos_catalog.json          # Master cache katalog video
    └── transcripts/                 # Cache subtitle raw VTT
```

---

## 🚀 Cara Menjalankan Pipeline Otomatisasi

### 1. Prasyarat
- Python 3.10+
- `yt-dlp` terpasang di sistem (`yt-dlp --version`)
- 9Router AI Gateway aktif di `http://127.0.0.1:20128`

### 2. Menjalankan Batch Ringkasan

**Menjalankan batch 5 video (default pilot run):**
```bash
python3 pipeline/run_pipeline.py --limit 5
```

**Menjalankan 1 video spesifik berdasarkan Video ID:**
```bash
python3 pipeline/run_pipeline.py --video-id XX70znd19h4
```

**Memperbarui ulang Master Index (MOC) tanpa scraping ulang:**
```bash
python3 pipeline/generate_moc.py
```

---

## 📖 Cara Menggunakan di Obsidian

1. Buka aplikasi **Obsidian**.
2. Pilih **"Open folder as vault"**.
3. Pilih folder repositori ini: `ringkasan-pecah-telur-channel`.
4. Buka file **`00 - Index Pecah Telur.md`** sebagai beranda navigasi utama Anda.
5. Gunakan **Graph View** di Obsidian untuk melihat keterhubungan antar bisnis, kategori, dan wilayah.

---

## ⚖️ Lisensi & Disclaimer
Konten wawancara asli merupakan hak cipta sepenuhnya milik **Channel YouTube Pecah Telur**. Repositori ini dibuat untuk tujuan edukasi, apresiasi wirausaha Indonesia, dan studi kasus bisnis.
