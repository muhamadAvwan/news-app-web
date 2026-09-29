# Dewan Berita Dunia — Web

Portal berita agregator: frontend statis + Vercel Functions (Python, stdlib saja, tanpa dependensi, tanpa database, tanpa API key).

## Struktur

```
├── index.html        # Frontend (satu file)
├── api/
│   └── news.py       # Vercel Function: ambil RSS 10 sumber + klasifikasi kata kunci
├── vercel.json
└── .gitignore
```

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `GET /` | Halaman utama (statis) |
| `GET /api/news` | JSON berita terklasifikasi (cache CDN 2 menit) |
| `GET /api/health` | Cek hidup |

## Deploy ke Vercel

1. Import repo ini di [vercel.com/new](https://vercel.com/new)
2. Deploy (tanpa setting apapun)
3. Selesai — langsung jalan

## Terjemahan bahasa Indonesia

Terjemahan memakai **fitur bawaan browser**, tanpa server tambahan:

1. **Default** (Brave/Chrome versi baru): tombol 🇮🇩 memakai *Translator API* on-device bawaan browser. Hasil disimpan di cache browser (localStorage) selama 14 hari.
2. **Fallback** (browser tanpa API): halaman menampilkan petunjuk untuk **klik kanan → "Terjemahkan ke Bahasa Indonesia"** (Brave/Chrome) — semua isi halaman termasuk judul berita akan diterjemahkan browser.

## Catatan

- Tidak ada API key dan tidak ada database — aman dipublikasikan.
- Klasifikasi memakai otak sederhana (kata kunci), bukan AI berbayar.