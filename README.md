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
| `GET /api/config` | Konfigurasi runtime (membaca env var `TRANSLATE_URL`) |
| `GET /api/health` | Cek hidup |

## Deploy ke Vercel

1. Fork / import repo ini di [vercel.com/new](https://vercel.com/new)
2. Deploy (tanpa setting apapun — langsung jalan)
3. (Opsional) Set environment variable `TRANSLATE_URL` berisi URL layanan penerjemah, contoh: `https://nama-space.hf.space/translate` — lihat repo `news-app-translate`

## Catatan

- Tidak ada API key dan tidak ada database — aman dipublikasikan.
- Terjemahan bahasa Indonesia dilayani oleh service terpisah (repo `news-app-translate`, Argos Translate) dan dikonfigurasi via env var `TRANSLATE_URL`.
- Cache terjemahan disimpan di browser (localStorage) selama 14 hari.
