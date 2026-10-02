# Dewan Berita Dunia — Web

Portal berita agregator: frontend statis + Vercel Functions (Python, stdlib saja, tanpa dependensi, tanpa database, tanpa API key).

## Struktur

```
├── index.html        # Frontend (satu file)
├── api/
│   └── news.py       # Vercel Function: 340 sumber (RSS + Atom + Mastodon + Steam API) + klasifikasi
├── vercel.json
└── .gitignore
```

## Sumber media sosial (feed resmi, gratis, tanpa API key)

Sumber sosial yang dipakai semuanya **feed resmi**, bukan scraping:

| Jenis | Cara akses | Jumlah |
|---|---|---|
| YouTube channel | `youtube.com/feeds/videos.xml?channel_id=…` (Atom) | 66 channel |
| GitHub releases | `github.com/<owner>/<repo>/releases.atom` (Atom) | 33 tool |
| Mastodon (cyber) | `infosec.exchange/@<akun>.rss` (RSS) | 14 akun |
| Komunitas (cyber) | `lobste.rs/t/<tag>.rss`, `hnrss.org/newest?q=…` | 6 feed |
| Steam app news | `api.steampowered.com/ISteamNews/GetNewsForApp/v2` (JSON) | 8 game |

**YouTube — game.** 11 media game (IGN, GameSpot, PC Gamer, Eurogamer, Polygon, GamesRadar, Digital Foundry, Giant Bomb, Jalur<Game, SantoS Gaming, Kotaku), 8 channel resmi (**PlayStation, Xbox, Nintendo of America, Steam, Ubisoft, SEGA, Blizzard, Riot Games**), 3 channel esports (**VALORANT, LoL Esports, ESL Counter-Strike**). Feed Atom sudah dibaca lewat `parse_atom()`; video `/shorts/` dibuang karena klip 1 menit, bukan berita.

**YouTube — sepak bola.** 28 channel resmi diverifikasi satu per satu lewat `channel_id` (bukan nama channel, supaya tidak tertukar akun): FIFA, UEFA, Premier League, Serie A, Ligue 1, Bundesliga, Liverpool, Arsenal, Manchester United, Real Madrid, Barcelona, Juventus, Inter, Tottenham, Chelsea, Dortmund, Bayern, PSG, Ajax, Celtic, Newcastle, Nottingham Forest, Roma, Feyenoord, Sevilla, Galatasaray, Al Ahly, Al Nassr. Club besar yang tidak punya channel resmi aktif tidak dipaksakan.

**YouTube — keamanan siber.** 16 channel tervalidasi: NetworkChuck, John Hammond, IppSec, David Bombal, LiveOverflow, SpecterOps, HackerSploit, Security Now, NetSPI, PwnFunction, Bishop Fox, NCC Group, Assetnote, Tricentis, InsiderPhD, sudo room. Diverifikasi nama **dan** `channel_id`-nya supaya tidak tertukar akun. Burst paralel ~20 request bikin YouTube membalas `404` yang tak terbedakan dari channel mati, jadi `fetch_feed()` mengulang sekali dengan jeda 1,5 detik khusus URL `youtube.com/feeds`.

**Mastodon & komunitas — keamanan siber.** Mastodon menyediakan RSS resmi per akun (`infosec.exchange/@<akun>.rss`), jadi tidak butuh API key dan tidak rapuh seperti scraping. 14 akun aktif dipakai: briankrebs, malwaretech, SwiftOnSecurity, cyb3rops, thegrugq, hacks4pancakes, malwarejake, lcamtuf, 0xabad1dea, JackRhysider, k8em0, mubix, ryanaraine, mattjay. Feed Mastodon tidak mengisi `<title>` (isi postingan ada di `<description>`), jadi `parse_rss()` menurunkan judul dari deskripsi dan `make_item()` **tidak** membuang deskripsi untuk feed bertanda `social`, lalu `keyword_classify()` ikut menilai deskripsi agar bidang cyber-nya terdeteksi. Sitiran non-keamanan (mis. post soal kopi) tersaring oleh filter kata kunci. Komunitas link memakai **Lobsters** (`/t/security.rss`, `/t/privacy.rss`) dan **Hacker News** (`hnrss.org/newest?q=…`); HN frontpage sengaja tidak dipakai karena terlalu berisik.

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
| **RSS langsung klub sepak bola** | 71 kandidat diuji, sebagian besar 404/403. Diganti Google News per klub + YouTube resmi. |
| **Channel YouTube PSSI / Liga Indonesia** | Tidak ditemukan channel yang aktif dan terverifikasi. Cakupan Indonesia mengandalkan media dan Google News. |

Kalau nanti mau X/Twitter, satu-satunya jalan: **self-host RSSHub** (Docker, Node) lalu pakai route-nya.

## Kategori

| Kode | Tab | Isi |
|---|---|---|
| `GENTING` | Genting / Urgent | perang, bencana, darurat nasional |
| `GAME` | Game / Update | patch, DLC, rilis, pengumuman game |
| `ESPORTS` | Esports | tournament, roster, match |
| `REVIEW_GAME` | Review Game | review, hands-on, impressions |
| `HARDWARE` | Hardware Gaming | GPU, CPU, laptop, konsol, periferal |
| `BOLA` | Sepak Bola | berita bola internasional, klub besar, pemain |
| `BOLA_LIGA` | Liga & Kompetisi | Liga Champions, Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Piala Dunia |
| `BOLA_TRANSFER` | Transfer | bursa transfer, rekrut, kontrak, loan |
| `BOLA_NASIONAL` | Timnas & Liga 1 | Timnas Indonesia/PSSI, Liga 1–3, klub Indonesia, pemain Indonesia |
| `CYBER_VULN` | Kerentanan & CVE | zero-day, CVE, security advisory, patch, KEV, CISA |
| `CYBER_MALWARE` | Malware & Ransomware | ransomware, infostealer, trojan, botnet, DDoS |
| `CYBER_APT` | Threat Intel & APT | APT, nation-state, threat actor, laporan vendor |
| `CYBER_BREACH` | Kebocoran Data | data breach, kebocoran data pribadi, database bocor |
| `CYBER_BUG` | Bug Bounty & Pentest | bug bounty, HackerOne/Bugcrowd, PoC, red team, writeup |
| `CYBER_TOOL` | Tool Offensive & Red Team | rilis tool, exploit framework, C2, fuzzing, offensive |
| `CYBER_BLUE` | Blue Team / DFIR / SOC | incident response, DFIR, threat hunting, deteksi |
| `CYBER_CLOUD` | Cloud & Container | cloud security, Kubernetes, container, supply chain |
| `CYBER_APP` | AppSec & Web | OWASP, AppSec, XSS/SSRF, API security |
| `CYBER_RE` | Reverse Engineering | reverse engineering, Ghidra/IDA, analisis biner |
| `CYBER_AI` | AI Security | prompt injection, LLM security, deepfake, model poisoning |
| `CYBER_GRC` | Regulasi & GRC | regulasi, compliance, GDPR/NIS2, UU PDP |
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

`balance_categories()` membagi per keluarga sesuai `FAMILY_SHARE`: kategori non-game (Genting/Politik/Trader/Lainnya) dapat jatah dulu secara giliran, lalu kategori game dibagi **giliran per genre**, lalu bola dibagi **giliran per kategori**, dan cyber dibagi **giliran per kategori**. Tanpa tahap per-genre, genre minim berita seperti Strategy akan selalu kalah dan tabnya kosong; tanpa tahap per-kategori, bola/cyber yang paling ramai akan menimpa yang lain.

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `GET /` | Halaman utama (statis) |
| `GET /api/news` | JSON berita terklasifikasi (cache CDN 2 menit) |
| `GET /api/health` | Cek hidup |

## Cara klasifikasi news

Dua lapis, supaya berita game tidak tenggelam oleh keyword umum:

1. **Tag sumber.** Tiap `SOURCES` punya field `topic` (`game` / `esports` / `hardware` / `bola` / `cyber`). Artikel dari sumber bertopic itu **tidak pernah** masuk `GENTING` — jadi "Warhammer" tidak salah jadi berita perang, dan "Citrix zero-day exploited" tidak salah jadi berita serangan militer.
2. **Kata kunci.** `GAME_KW` memisahkan sub-kategori: kata `review`/`hands-on` → `REVIEW_GAME`, `esports`/`tournament` → `ESPORTS`, `gpu`/`rtx`/`laptop` → `HARDWARE`, sisanya → `GAME`.

Sumber berita umum (BBC, CNBC, Google News politik) tetap pakai jalur lama, tapi berita game di dalamnya ditangkap `GAME_KW`.

`balance_categories()` membagi kuota artikel **secara giliran** antar kategori, jadi tab politik tidak kosong walau Sembilan feed game mengirim ratusan artikel per jam. Urutan akhir tetap berdasarkan hotness.

## Sepak bola

Cakupan 89 sumber: **28 channel YouTube resmi** (league & club), **14 media** (BBC, Guardian, 90min, Sky Sports, Yahoo Soccer, Standard, Kicker, Planet Football, Bundesliga, CNN Indonesia, detikSport, Sindonews, Tribun, Nusantara Post), dan **47 query Google News** dengan `when:7d` supaya tidak ada artikel lama yang tak pernah tenggelam.

Query-nya dibagi per **orang/perusahaan**:

- **Liga & kompetisi** — Liga Champions, Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Piala Dunia 2026, Liga Europa, Liga Klub Dunia.
- **Klub** — Manchester United, Liverpool, Real Madrid, Barcelona, Bayern, Inter, Arsenal, Chelsea, PSG, Juventus, plus klub Indonesia: Persib, Persija, Persebaya, Arema, Bali United, PSM Makassar, Persipura, Persela Solo.
- **Pemain** — Cristiano Ronaldo, Messi, Haaland, Salah, Mbappe, Vinicius Jr, Bellingham, Harry Kane, plus pemain Indonesia: Marselino Ferdinan, Jay Idzes, Ragnar Oratmangoen, Justin Hubner, Sandy Walsh, Asnawi Miftah.
- **Nasional** — Timnas Indonesia/PSSI, Liga 1-3, Piala Asia/ASEAN Cup.
- **Transfer** — bursa transfer empat liga besar dan transfer pemain Indonesia.

Cara kerjanya:

1. **Petunjuk sumber menang.** Tiap query bola dibuat khusus satu topik, jadi field `bola_cat` langsung menentukan tab tujuan. Kata kunci hanya cadangan untuk media umum seperti CNN/detik yang isinya campuran olahraga.
2. **Sumber bola tidak pernah jadi berita perang.** Kata `serangan` dan `bom` ada di `GENTING_KW`; tanpa penjaga, `Serangan Printz` di judul bola akan salah klasifikasi.
3. **Wajib ada sinyal sepak bola.** Query yang luas ("PSSI") kadang menarik halaman yang sama sekali bukan bola, jadi artikel tanpa satu pun kata kunci sepak bola langsung dibuang.
4. **Genre hanya untuk tab game.** Berita bola yang kebetulan kena kata kunci game ("FIFA 26", "RPG") tidak lagi muncul dengan chip genre yang menyesatkan.
5. **Filter halaman betting.** Query bola banyak menarik halaman betting yang menyamar sebagai berita; pola `SPAM_RE` membuangnya sebelum tampil.

### Quota empat keluarga

`balance_categories()` membagi kuota per **keluarga** (`FAMILY_SHARE`: 0,10 other / 0,24 game / 0,24 bola / 0,42 cyber), masing-masing memakai **giliran** dengan plafon `MAX_PER_CAT` per kategori. Porsi tiap keluarga dibaca sebagai **tambahan** (`len(kept) - start < budget`), bukan ambang total — kalau tidak, hanya keluarga pertama yang terisi. Tanpa keluarga, cyber (baru, paling sedikit arsipnya) akan tersapu oleh game/bola yang feed-nya jauh lebih rajin.

## Keamanan siber

Cakupan 163 sumber:

- **41 media & riset** — The Hacker News, BleepingComputer, SecurityWeek, The Record, Dark Reading, Help Net Security, Schneier, Security Affairs, Krebs, WeLiveSecurity, Securelist, Malwarebytes, Avast, MalwareTips, Virus Bulletin, Recorded Future, Red Canary, CrowdStrike, SentinelOne Labs, Horizon3, Check Point Research, Unit 42, Wiz, Snyk, Microsoft Security, Google Security/Cloud TI/Project Zero, AWS Security, SANS ISC, Chrome Releases, PortSwigger Research, InfoSec Writeups, Hacking Articles, Exploit-DB, GitHub Blog, Kali Linux, Trail of Bits, Binarly, ANY.RUN.
- **14 akun Mastodon + 6 feed komunitas** — Mastodon (`infosec.exchange`), Lobsters (security, privacy), dan Hacker News (security, vulnerability, ransomware, reverse engineering). Lihat bagian sumber media sosial.
- **33 rilis tool resmi** — feed `releases.atom` proyeknya sendiri: ProjectDiscovery (nuclei, httpx, subfinder, katana, naabu, interactsh, cloudlist, nuclei-templates), Metasploit, OWASP ZAP, sqlmap, nikto, ffuf, Amass, chisel, bettercap, Sliver, BloodHound, BBOT, Impacket, Semgrep, gitleaks, trufflehog, SecLists, PwnDoc, CyberChef, YARA, Suricata, Volatility3, Trivy, WPScan, Juice Shop.
- **16 channel YouTube** (lihat atas).
- **53 query Google News** `when:7d` — kerentanan/CVE, malware, APT, kebocoran data, bug bounty, tool, blue team, cloud, appsec, reverse engineering, AI security, dan regulasi; juga versi Indonesia. Tiap query diberi petunjuk salah satu dari **12 bidang cyber**.

Cara kerjanya:

1. **Feed rilis untuk tool.** Google News hampir tidak meliput rilis tool, jadi sumber tool utama adalah `releases.atom` first-party. Judulnya cuma nomor versi ("v3.11.1"), makanya `make_item()` memprefiks nama tool → "nuclei rilis v3.11.1".
2. **Sumber cyber tidak pernah jadi berita perang.** Kata `attack`, `exploit`, dan `breach` ada di `GENTING_KW`; cabang `topic == "cyber"` dicek **sebelum** `GENTING` supaya kerentanan tidak salah jadi berita perang.
3. **Sinyal anti-noise.** Artikel cyber wajib punya minimal satu kata kunci inti, dan media umum (BBC/Reuters) butuh minimal **dua** supaya kata `breach`/`exploit` yang muncul di konteks lain tidak ikut terambil.
4. **Routing 12 bidang.** Sumber yang memang khusus satu bidang punya petunjuk `cyber_cat`. Untuk media umum, bidang dengan skor kata kunci tertinggi yang dipakai (`cyber_category`), cadangannya `CYBER_APT`.
5. **Kata kunci kategori dipertajam.** Frasa umum seperti `guide`, `tutorial`, `findings`, `hunter`, `tool`, `framework`, `release`, `fine`, `standard` dibuang karena menarik berita non-cyber ("Command and Control Centre" milik dinas darurat, "bounty hunter", "Weight: fine", "non-compliance"). Feed rilis tetap lolos lewat sinyal pola versi (`v0`…`v9`, `rilis`).
6. **Post sosial wajib bersinyal bidang.** Feed Mastodon isinya pendek dan sering menyinggung kata umum ("Hacker News", nama podcast), jadi post sosial hanya lolos kalau ada kata kunci bidang yang jelas. Isi postnya ada di `<description>`; `parse_rss()` menurunkan judul dari situ dan `make_item()` tidak membuang deskripsi untuk feed `social`.

### Yang **gagal** untuk cyber (sudah diuji)

| Sumber | Hasil uji |
|---|---|
| **CISA** (`cisa.gov` feeds) | `403` anti-bot. |
| **Microsoft MSRC** | XML tidak valid / bukan feed RSS. |
| **Mandiant, Cure53, GTFOBins, Syzbot** | `404`. |
| **Packet Storm** | handshake SSL gagal. |
| **HackerOne** | format RSS tidak cocok. |
| **Google News "tool baru" / "OSINT" / "pentest writeup"** | hampir kosong atau noise; ditutup oleh feed rilis GitHub. |

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
- Semua RSS yang dipakai sudah diuji hidup. Yang ditolak (403 anti-bot): Kotaku, Nintendo Life, Dot Esports, VideoCardz, CISA.
- Deskripsi Google News yang cuma mengulang judul dibuang di `make_item()` (83% kasus) supaya payload tidak bengkak tanpa menambah informasi.
- Ukuran payload: ~790 artikel, ~500 KB mentah / ~200 KB gzip, refresh ~6 detik (batas Vercel 30 detik).