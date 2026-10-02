# Dewan Berita Dunia — Web

Portal berita agregator: frontend statis + Vercel Functions (Python, stdlib saja, tanpa dependensi, tanpa database, tanpa API key).

## Struktur

```
├── index.html        # Frontend (satu file)
├── api/
│   └── news.py       # Vercel Function: 88 sumber (RSS + Atom + Steam API) + klasifikasi
├── vercel.json
└── .gitignore
```

## Sumber media sosial (feed resmi, gratis, tanpa API key)

Sumber sosial yang dipakai semuanya **feed resmi**, bukan scraping:

| Jenis | Cara akses | Jumlah |
|---|---|---|
| YouTube channel | `youtube.com/feeds/videos.xml?channel_id=…` (Atom) | 22 channel |
| Steam app news | `api.steampowered.com/ISteamNews/GetNewsForApp/v2` (JSON) | 8 game |

**YouTube** — 11 media game (IGN, GameSpot, PC Gamer, Eurogamer, Polygon, GamesRadar, Digital Foundry, Giant Bomb, Jalur<Game, SantoS Gaming, Kotaku), 8 channel resmi (**PlayStation, Xbox, Nintendo of America, Steam, Ubisoft, SEGA, Blizzard, Riot Games**), 3 channel esports (**VALORANT, LoL Esports, ESL Counter-Strike**). Feed Atom sudah dibaca lewat `parse_atom()`; video `/shorts/` dibuang karena klip 1 menit, bukan berita.

**Steam** — paling cepat: patch notes resmi keluar di sini sebelum liputan mana pun. Hanya game yang hub-nya dipakai developer untuk patch resmi (CS2, Dota 2, TF2, Portal 2, Terraria, Lethal Company, Elden Ring Nightreign, Path of Exile). Game yang hub-nya dipakai user (mis. GTA V) sengaja dibuang karena isinya sampah.

**Boost sumber.** Field `boost` menaikkan peringkat: pengumuman resmi first-party (PlayStation/Xbox/Nintendo/Steam) `+13`, channel esports & publisher `+12`, media game & kreator Indonesia `+8`, Steam API `+14`. Jadi pengumuman asli muncul di atas rumor.

### Yang **tidak** bisa dipakai (sudah diuji, hasilnya jelek)

| Platform | Hasil uji |
|---|---|
| **X / Twitter** | API resmi berbayar ($100/bulan). Semua Nitter sudah mati, instance RSSHub publik 403/404, rss-bridge 500. **Tidak mungkin tanpa API key.** |
| **Reddit** | `.rss` jalan **satu** request lalu langsung `429 Too Many Requests` dari IP server. Tidak stabil di Vercel. |
| **Bluesky** | API publiknya membalas `403/401` dari IP ini. Mungkin jalan di region lain, tapi tidak bisa diverifikasi. |
| **TikTok / Instagram / Facebook** | Tidak ada RSS publik; balasan hanya HTML. Butuh scraping (rapuh & melanggar ToS). |
| **Kotaku, Nintendo Life, Dot Esports, VideoCardz** | RSS 403 anti-bot. |

Kalau nanti mau X/Twitter, satu-satunya jalan: **self-host RSSHub** (Docker, Node) lalu pakai route-nya.

## Kategori

| Kode | Tab | Isi |
|---|---|---|
| `GENTING` | Genting / Urgent | perang, bencana, darurat nasional |
| `GAME` | Game / Update | patch, DLC, rilis, pengumuman game |
| `ESPORTS` | Esports | tournament, roster, match |
| `REVIEW_GAME` | Review Game | review, hands-on, impressions |
| `HARDWARE` | Hardware Gaming | GPU, CPU, laptop, konsol, periferal |
| `POLITIK_ID` | Politik Dalam Negeri | kebijakan, hukum, ekonomi |
| `POLITIK_INT` | Politik Internasional | sengketa, diplomasi, geopolitik |
| `TRADER` | Trader / Pasar | saham, crypto, Forex, emas |
| `LAINNYA` | Lainnya | sisa |

## Genre game

Ada **23 genre**, tampil sebagai baris chip di bawah tab kategori (sub-filter, jadi `Tab + Genre` bisa digabung):

`RPG`, `FPS`, `Tactical`, `Battle Royale`, `MOBA`, `MMO`, `Strategy`, `Survival`, `Horror`, `Action`, `Adventure`, `Open World`, `Roguelike`, `Platformer`, `Fighting`, `Sports`, `Racing`, `Simulation`, `Puzzle`, `Card / Gacha`, `Sandbox`, `Metroidvania`, `Rhythm`

Cara kerjanya:

1. **Feed khusus genre.** 26 query Google News (23 genre, plus 3 versi Bahasa Indonesia untuk RPG/MOBA/Horror) jadi sumber tersendiri, sehingga genre yang tidak punya media khusus tetap terisi.
2. **Deteksi dari isi, bukan asal sumber.** `detect_genres()` memakai judul + nama sumber dengan pencocokan **batas kata**. Tanpa batas kata, `rts` ikut cocok di "eSports" dan `eco` ikut cocok di "Economic", sehingga berita politik ikut bertag Strategy/Sandbox.
3. **Sumber berbentuk domain diabaikan.** `mmorpg.com` dan `platformer.news` tidak menyumbang sinyal genre - yang cocok cuma nama situsnya, bukan isi beritanya.
4. **Filter anti-sampah.** Query Google News yang terlalu luas (mis. "Rust") menarik artikel yang bukan game. Artikel dari feed genre yang judulnya tidak cocok dengan genrenya langsung dibuang.
5. **Multi-label.** Satu artikel bisa punya beberapa genre, diurutkan dari yang paling kuat; `genre_main` dipakai untuk pengimbangan kuota.

`balance_categories()` jalan dua tahap: kategori non-game (Genting/Politik/Trader/Lainnya) dapat jatah lebih dulu secara giliran, lalu kategori game dibagi **giliran per genre**. Tanpa tahap kedua genre minim berita seperti Strategy akan selalu kalah dan tabnya kosong.

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `GET /` | Halaman utama (statis) |
| `GET /api/news` | JSON berita terklasifikasi (cache CDN 2 menit) |
| `GET /api/health` | Cek hidup |

## Cara klasifikasi news

Dua lapis, supaya berita game tidak tenggelam oleh keyword umum:

1. **Tag sumber.** Tiap `SOURCES` punya field `topic` (`game` / `esports` / `hardware`). Artikel dari sumber bertopic itu **tidak pernah** masuk `GENTING` — jadi "Warhammer" tidak salah jadi berita perang.
2. **Kata kunci.** `GAME_KW` memisahkan sub-kategori: kata `review`/`hands-on` → `REVIEW_GAME`, `esports`/`tournament` → `ESPORTS`, `gpu`/`rtx`/`laptop` → `HARDWARE`, sisanya → `GAME`.

Sumber berita umum (BBC, CNBC, Google News politik) tetap pakai jalur lama, tapi berita game di dalamnya ditangkap `GAME_KW`.

`balance_categories()` membagi kuota artikel **secara giliran** antar kategori, jadi tab politik tidak kosong walau Sembilan feed game mengirim ratusan artikel per jam. Urutan akhir tetap berdasarkan hotness.

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
- Setiap response menyertakan `sources_ok` / `sources_fail` supaya tahu feed mana yang sedang mati.
- Semua RSS yang dipakai sudah diuji hidup. Yang ditolak (403 anti-bot): Kotaku, Nintendo Life, Dot Esports, VideoCardz.