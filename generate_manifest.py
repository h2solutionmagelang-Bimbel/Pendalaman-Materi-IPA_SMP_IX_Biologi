#!/usr/bin/env python3
"""
generate_manifest.py
Memindai folder ini untuk file kuis/asesmen HTML, mengambil judulnya
(dari tag <title> atau <h1>), lalu menulis manifest.js yang dibaca
oleh index.html.

CARA PAKAI:
1. Taruh skrip ini di folder yang sama dengan semua file kuis HTML
   dan index.html.
2. Setiap kali menambah/menghapus/mengganti nama file kuis, jalankan:
       python generate_manifest.py
3. Buka (atau refresh) index.html — daftar akan otomatis terbarui.

Skrip ini TIDAK berjalan otomatis sendiri saat upload — harus
dijalankan manual (atau dijadwalkan) setiap ada perubahan file.
Tidak ada cara membuatnya benar-benar real-time tanpa server backend.
"""
import json
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
EXCLUDE = {"index.html", "index_files"}
OUTPUT = os.path.join(ROOT, "manifest.js")


# Kata kunci untuk menebak kategori mata pelajaran dan jenis asesmen dari
# judul/nama file. Ini HEURISTIK (tebakan berbasis kata kunci), bukan
# pembacaan metadata sebenarnya — tambahkan kata kunci sendiri di bawah
# jika ada pola penamaan lain yang Anda pakai.
SUBJECT_KEYWORDS = [
    ("Kimia", ["kimia", "elektrolisis", "faraday", "atom", "sel volta", "tata nama"]),
    ("IPA", ["ipa", "pernapasan", "peredaran darah", "reproduksi", "pewarisan sifat"]),
    ("Matematika", ["matematika", "aritmatika", "geometri", "aljabar"]),
    ("Fisika", ["fisika"]),
    ("Biologi", ["biologi"]),
]
TYPE_KEYWORDS = [
    ("ASTS", ["asts"]),
    ("TryOut", ["tryout", "try out"]),
    ("Asesmen Formatif", ["asesmen formatif", "formatif"]),
    ("LKPD", ["lkpd"]),
    ("Tugas Mandiri", ["tugas mandiri", "tugas"]),
]


def guess_from_keywords(text, keyword_table, default):
    text_low = text.lower()
    for label, keywords in keyword_table:
        if any(kw in text_low for kw in keywords):
            return label
    return default


def extract_title(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(8000)  # cukup baca bagian awal file
        m = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
            if title:
                return title
        m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1))
            title = re.sub(r"\s+", " ", title).strip()
            if title:
                return title
    except Exception as e:
        print(f"  ! Gagal membaca {filepath}: {e}")
    return None


def estimate_question_count(filepath):
    """
    Perkiraan KASAR jumlah soal, dengan mencari pola umum yang biasa dipakai
    di file kuis (data-soal, class="soal", "soal_id", dsb). TIDAK dijamin
    akurat untuk semua format — kembalikan None kalau tidak yakin, supaya
    index.html tidak menampilkan angka palsu yang meyakinkan.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return None

    patterns = [
        r'data-soal-id\s*=\s*"',
        r'data-question-id\s*=\s*"',
        r'class="[^"]*\bsoal-item\b',
        r'class="[^"]*\bquestion-card\b',
    ]
    for pat in patterns:
        count = len(re.findall(pat, content, re.IGNORECASE))
        if count >= 3:  # ambang minimal supaya bukan kebetulan cocok 1-2x
            return count
    return None


def main():
    quizzes = []
    for fname in sorted(os.listdir(ROOT)):
        if not fname.lower().endswith(".html") or fname in EXCLUDE:
            continue
        fpath = os.path.join(ROOT, fname)
        title = extract_title(fpath) or fname
        mtime = os.path.getmtime(fpath)
        combined_text = f"{title} {fname}"
        quizzes.append({
            "file": fname,
            "title": title,
            "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
            "subject": guess_from_keywords(combined_text, SUBJECT_KEYWORDS, "Umum"),
            "type": guess_from_keywords(combined_text, TYPE_KEYWORDS, "Kuis"),
            "question_count": estimate_question_count(fpath),  # None jika tak yakin
        })

    # Terbaru di atas
    quizzes.sort(key=lambda q: q["modified"], reverse=True)

    js_content = (
        "// File ini digenerate otomatis oleh generate_manifest.py.\n"
        "// JANGAN diedit manual — perubahan akan hilang saat skrip dijalankan ulang.\n"
        "const QUIZ_MANIFEST = "
        + json.dumps(quizzes, ensure_ascii=False, indent=2)
        + ";\n"
    )

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"Selesai. {len(quizzes)} file kuis ditemukan.")
    for q in quizzes:
        print(f"  - {q['title']}  ({q['file']})")
    print(f"Ditulis ke: {OUTPUT}")


if __name__ == "__main__":
    main()
