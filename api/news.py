import concurrent.futures as cf
import datetime as dt
import email.utils as eut
import hashlib
import html as htmllib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CATS = [
    ("GENTING", "Genting / Urgent", "#ff4d4d"),
    ("GAME", "Game / Update", "#35d07f"),
    ("ESPORTS", "Esports", "#ff7ac6"),
    ("REVIEW_GAME", "Review Game", "#ff9f43"),
    ("HARDWARE", "Hardware Gaming", "#22d3ee"),
    ("POLITIK_ID", "Politik Dalam Negeri", "#4da6ff"),
    ("POLITIK_INT", "Politik Internasional", "#8a6dff"),
    ("TRADER", "Trader / Pasar", "#ffc14d"),
    ("LAINNYA", "Lainnya", "#7a8290"),
]

# Kategori yang hanya boleh diisi oleh sumber bertopic game
GAME_CATS = ["GAME", "ESPORTS", "REVIEW_GAME", "HARDWARE"]

# Batas jumlah artikel akhir per kategori supaya tiap tab berisi.
# Genre butuh ruang lebih: 23 genre harus tetap punya isinya setelah
# pengimbangan kategori, jadi kuota per kategori dilonggarkan.
MAX_ARTICLES = 520
MAX_PER_CAT = 90

SOURCES = [
    {
        "name": "Google News Indonesia",
        "url": "https://news.google.com/rss?hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
    },
    {
        "name": "Google News Nasional",
        "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
    },
    {
        "name": "Google News Bisnis ID",
        "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
    },
    {
        "name": "Google News Ekonomi ID",
        "url": "https://news.google.com/rss/search?q=(saham+OR+inflasi+OR+rupiah+OR+bursa+OR+suku+bunga)&hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
    },
    {
        "name": "Google News Dunia",
        "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
    },
    {
        "name": "Google News Politik Dunia",
        "url": "https://news.google.com/rss/search?q=(election+OR+parliament+OR+summit+OR+war+OR+diplomacy)&hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
    },
    {
        "name": "Google News Pasar Global",
        "url": "https://news.google.com/rss/search?q=(stocks+OR+fed+OR+inflation+OR+oil+OR+bitcoin)&hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
    },
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "country": "WORLD",
        "lang": "en",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "country": "WORLD",
        "lang": "en",
    },
    {
        "name": "CNBC World",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
        "country": "WORLD",
        "lang": "en",
    },
    {
        "name": "IGN",
        "url": "https://feeds.ign.com/ign/games-all",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "PC Gamer",
        "url": "https://www.pcgamer.com/rss/",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Eurogamer",
        "url": "https://www.eurogamer.net/feed",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "GameSpot",
        "url": "https://www.gamespot.com/feeds/mashup/",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Gematsu",
        "url": "https://www.gematsu.com/feed",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "VGC",
        "url": "https://www.videogameschronicle.com/feed/",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Game Developer",
        "url": "https://www.gamedeveloper.com/rss.xml",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "PCGamesN",
        "url": "https://www.pcgamesn.com/feed",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Rock Paper Shotgun",
        "url": "https://www.rockpapershotgun.com/feed",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "GamesIndustry.biz",
        "url": "https://www.gamesindustry.biz/feed",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "HLTV Esports",
        "url": "https://www.hltv.org/rss/news",
        "country": "WORLD",
        "lang": "en",
        "topic": "esports",
    },
    {
        "name": "Tom's Hardware",
        "url": "https://www.tomshardware.com/feeds/all",
        "country": "WORLD",
        "lang": "en",
        "topic": "hardware",
    },
    {
        "name": "TechPowerUp",
        "url": "https://www.techpowerup.com/rss/news",
        "country": "WORLD",
        "lang": "en",
        "topic": "hardware",
    },
    {
        "name": "Google News Game",
        "url": "https://news.google.com/rss/search?q=gaming+OR+%22video+game%22+OR+esports&hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Google News Game ID",
        "url": "https://news.google.com/rss/search?q=game+OR+gaming+OR+esports&hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
        "topic": "game",
    },
    {
        "name": "Google News Esports ID",
        "url": "https://news.google.com/rss/search?q=esports+OR+turnamen+game+OR+game+online&hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
        "topic": "esports",
    },
    {
        "name": "Google News Konsol ID",
        "url": "https://news.google.com/rss/search?q=(PlayStation+OR+PS5+OR+Xbox+OR+Switch+OR+Steam)&hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
        "topic": "game",
    },
    {
        "name": "Google News Hardware Game ID",
        "url": "https://news.google.com/rss/search?q=(GPU+OR+RTX+OR+AMD+OR+Intel+Arc+OR+PS5+OR+Xbox)+hardware&hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
        "topic": "hardware",
    },
    {
        "name": "Eurogamer Reviews",
        "url": "https://www.eurogamer.net/feed/reviews",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Google News Review Game",
        "url": "https://news.google.com/rss/search?q=(review+OR+%22hands-on%22)+(%22video+game%22+OR+PS5+OR+Xbox+OR+Steam)&hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
    },
    {
        "name": "Google News Review Game ID",
        "url": "https://news.google.com/rss/search?q=(review+OR+ulasan)+game+(PS5+OR+Xbox+OR+PC+OR+Switch)&hl=id&gl=ID&ceid=ID:id",
        "country": "ID",
        "lang": "id",
        "topic": "game",
    },
    {
        "name": "Google News Esports",
        "url": "https://news.google.com/rss/search?q=esports+OR+%22e-sports%22+OR+tournament+league+of+legends+OR+valorant+OR+counter-strike&hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
        "topic": "esports",
    },
]

# --- Sumber sosial resmi (feed resmi, gratis, tanpa API key) ---
# YouTube: tiap channel punya feed resmi /feeds/videos.xml?channel_id=...
# (channel_id sudah diverifikasi, bukan handle, supaya tidak perlu lookup tiap request)
# Kolom keempat = boost: sumber resmi/pertama-party (=pengumuman asli, bukan
# rumor) diberi nilai lebih tinggi supaya naik di tab "Semua".
YT_CHANNELS = [
    ("UCKy1dAqELo0zrOtPkf0eTMw", "IGN", "game", 8),
    ("UC5CE6nbu1tjSGha-a_cHAFA", "GameSpot", "game", 8),
    ("UCk2ipH2l8RvLG0dr-rsBiZw", "PC Gamer", "game", 8),
    ("UCciKycgzURdymx-GRSY2_dA", "Eurogamer", "game", 8),
    ("UCuVxaQDraOja6xKidcmoufA", "Polygon", "game", 8),
    ("UCgaPRP68bbyHnfkPhWWBrNw", "GamesRadar", "game", 8),
    ("UCLdBr5f6RcP6l_TAP4GkhDQ", "Digital Foundry", "game", 9),
    ("UCmeds0MLhjfkjD_5acPnFlQ", "Giant Bomb", "game", 8),
    ("UCgABLa_5bd6BB2ZYUg6rFfw", "Jalur<Game", "game", 9),
    ("UCvly1KenieSFtEHmJLTbswA", "SantoS Gaming", "game", 8),
    ("UCBsbrudhKRrT9zs8iNOEjjw", "PlayStation", "game", 13),
    ("UCydtMNspoPAlqBjFSGnigSw", "Xbox", "game", 13),
    ("UCGIY_O-8vW4rfX98KlMkvRg", "Nintendo of America", "game", 13),
    ("UCg0FSqPeiGD_lIiPaaAehQg", "Steam", "game", 13),
    ("UCBMvc6jvuTxH6TNo9ThpYjg", "Ubisoft", "game", 12),
    ("UCDKOsemhPLrK4JnsZqkxHLA", "SEGA", "game", 12),
    ("UClOf1XXinvZsy4wKPAkro2A", "Blizzard", "game", 12),
    ("UC2t5bjwHdUX4vM2g8TRDq5g", "Riot Games", "game", 12),
    ("UCA1d3HFGFUmkKr2JIUA5Vlw", "VALORANT", "esports", 12),
    ("UCSF_aFGIIIoWY30GVV19TKA", "LoL Esports", "esports", 12),
    ("UCDQZcZZwv-RhxHxJpHCdmbQ", "ESL Counter-Strike", "esports", 12),
    ("UCg5bOg1qVoZ2JDJ7MmjY63A", "Kotaku", None, 6),
]

# API resmi Steam, isi paling cepat (patch notes resmi game).
# Hanya game yang hub-nya dipakai developer untuk patch resmi — game yang
# hub-nya dipakai user (mis. GTA V) menghasilkan berita sampah, jadi dibuang.
STEAM_GAMES = [
    ("730", "Counter-Strike 2"),
    ("570", "Dota 2"),
    ("440", "Team Fortress 2"),
    ("620", "Portal 2"),
    ("105600", "Terraria"),
    ("1966720", "Lethal Company"),
    ("1599340", "ELDEN RING NIGHTREIGN"),
    ("238960", "Path of Exile"),
]

for _cid, _name, _topic, _boost in YT_CHANNELS:
    SOURCES.append({
        "name": "YT " + _name,
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=" + _cid,
        "country": "WORLD",
        "lang": "en",
        "topic": _topic,
        "kind": "atom",
        "boost": _boost,
    })

for _appid, _gname in STEAM_GAMES:
    SOURCES.append({
        "name": "Steam " + _gname,
        "label": _gname + " · Steam",
        "url": "https://store.steampowered.com/app/" + _appid,
        "appid": _appid,
        "count": 5,
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
        "kind": "steam",
        "boost": 14,
    })

# --- Sumber khusus per genre ---
# Query sengaja memakai JUDUL game spesifik, bukan kata umum. Kata umum
# ("Rust", "battle royale") pulls berita non-game: mis. "Supporting native Rust
# in Workers" adalah bahasa pemrograman, bukan game survival.
GENRE_QUERIES = [
    ("MOBA_EN", "MOBA", 'MOBA OR "League of Legends" OR "Dota 2" OR "Mobile Legends"'),
    ("RPG_EN", "RPG", '"Final Fantasy" OR "Elden Ring" OR JRPG OR "Baldur\'s Gate" OR Genshin'),
    ("FPS_EN", "FPS", '"Call of Duty" OR Battlefield OR "Counter-Strike 2" OR "Team Fortress" OR Halo'),
    ("TACTICAL_EN", "TACTICAL", '"Rainbow Six" OR XCOM OR "Ready or Not" OR "Total War"'),
    ("BATTLE_ROYALE_EN", "BATTLE_ROYALE", '"Apex Legends" OR PUBG OR Warzone OR "Fortnite" battle royale'),
    ("MMORPG_EN", "MMORPG", '"World of Warcraft" OR "Final Fantasy XIV" OR "Guild Wars 2" OR "Black Desert"'),
    ("STRATEGY_EN", "STRATEGY", '"StarCraft 2" OR "Age of Empires" OR "Civilization 7" OR "tower defense"'),
    ("SURVIVAL_EN", "SURVIVAL", '"Don\'t Starve" OR Valheim OR "The Long Dark" OR DayZ'),
    ("HORROR_EN", "HORROR", '"survival horror" OR "Resident Evil" OR "Dead Space" OR "Silent Hill" OR "Lethal Company"'),
    ("ACTION_EN", "ACTION", '"Devil May Cry" OR Sekiro OR Bayonetta OR "souls-like"'),
    ("ADVENTURE_EN", "ADVENTURE", '"The Last of Us" OR "Life is Strange" OR Uncharted OR "narrative adventure"'),
    ("OPEN_WORLD_EN", "OPEN_WORLD", '"open world" OR "Breath of the Wild" OR "Witcher 3" OR "Red Dead Redemption"'),
    ("ROGUELIKE_EN", "ROGUELIKE", 'roguelike OR roguelite OR Balatro OR "Slay the Spire" OR "Vampire Survivors"'),
    ("PLATFORMER_EN", "PLATFORMER", '"Super Mario" OR "Sonic" OR Celeste OR platformer'),
    ("FIGHTING_EN", "FIGHTING", 'Tekken OR "Street Fighter 6" OR "Mortal Kombat" OR "Guilty Gear"'),
    ("SPORTS_EN", "SPORTS", '"EA Sports FC" OR eFootball OR "NBA 2K" OR "Rocket League"'),
    ("RACING_EN", "RACING", '"Gran Turismo" OR "Forza Horizon" OR "Need for Speed" OR "Mario Kart"'),
    ("SIMULATION_EN", "SIMULATION", '"Stardew Valley" OR "The Sims 4" OR "Cities: Skylines" OR "flight simulator"'),
    ("PUZZLE_EN", "PUZZLE", '"puzzle game" OR "Candy Crush" OR Tetris OR "Portal 2"'),
    ("CARD_GACHA_EN", "CARD_GACHA", 'gacha OR "Marvel Snap" OR "Clash Royale" OR "Yu-Gi-Oh" OR "Hearthstone"'),
    ("SANDBOX_EN", "SANDBOX", 'Minecraft OR Terraria OR Roblox OR "sandbox game"'),
    ("METROIDVANIA_EN", "METROIDVANIA", 'metroidvania OR "Metroid Dread" OR Castlevania'),
    ("RHYTHM_EN", "RHYTHM", '"rhythm game" OR "Beat Saber" OR "osu!" OR "Just Dance"'),
    ("RPG_ID", "RPG", '"game rpg" OR "game anime" OR "game idle" OR "JRPG"'),
    ("MOBA_ID", "MOBA", '"Mobile Legends" OR "Honor of Kings" OR "game MOBA" OR "game online"'),
    ("HORROR_ID", "HORROR", 'game horor OR "game zombie" OR "game survival horror"'),
]

for _gname, _gcode, _q in GENRE_QUERIES:
    SOURCES.append({
        "name": "Genre " + _gname,
        "url": "https://news.google.com/rss/search?q="
               + urllib.parse.quote(_q) + "&hl=en-US&gl=US&ceid=US:en",
        "country": "WORLD",
        "lang": "en",
        "topic": "game",
        "genre": _gcode,
        "boost": 6,
    })

GENTING_KW = [
    "perang", "serangan", "invasi", "rudal", "nuklir", "bom", "ledakan", "tewas",
    "korban jiwa", "darurat", "bencana", "gempa", "tsunami", "banjir bandang",
    "kebakaran hebat", "pembunuhan", "kudeta", "krisis", "penembakan",
    "penyerangan", "sandera", "evakuasi", "lockdown", "pandemi", "wabah",
    "heat", "war", "attack", "strike", "killed", "dead", "death toll", "missile",
    "nuclear", "emergency", "earthquake", "tsunami", "explosion", "hostage",
    "invasion", "coup", "crisis", "crash", "shooting", "airstrike", "bombing",
    "clashes", "offensive", "collapse", "outbreak", "floods kill", "wildfire",
]
TRADER_KW = [
    "saham", "bursa", "ihsg", "wall street", "nasdaq", "dow jones", "s&p",
    "inflasi", "suku bunga", "bank indonesia", "bank sentral", "fed", "federal reserve",
    "rupiah", "dolar", "defisit", "resesi", "harga minyak", "emas", "komoditas",
    "nikel", "batu bara", "crypto", "bitcoin", "ethereum", "investasi", "tarif impor",
    "sanksi ekonomi", "apbn", "obligasi", "yield", "laporan keuangan", "dividen",
    "stocks", "stock market", "inflation", "interest rate", "central bank", "gdp",
    "recession", "bond", "gold price", "oil price", "crude", "commodity", "bitcoin",
    "cryptocurrency", "currency", "dollar", "euro", "trade deal", "tariff", "sanctions",
    "earnings", "rally", "selloff", "rate cut", "rate hike", "hawkish", "dovish",
]
POL_ID_KW = [
    "presiden", "prabowo", "jokowi", "menteri", "kabinet", "dpr", "mpr", "dpd",
    "partai", "pemilu", "pilpres", "pilkada", "pileg", "kpu", "bawaslu", "polri",
    "tni", "istana", "dprd", "mahkamah konstitusi", "mk ", "pemerintah indonesia",
    "indonesia", "jakarta", "gubernur", "bupati", "walikota", "kepresidenan",
]
POL_INT_KW = [
    "president", "prime minister", "parliament", "election", "senate", "congress",
    "white house", "kremlin", "european union", "united nations", "nato",
    "putin", "trump", "xi jinping", "macron", "netanyahu", "zelensky", "merkel",
    "diplomacy", "sanctions", "trade war", "geopolitik", "g7", "g20",
    "brics", "asean", "treaty", "ambassador", "regime", "election results",
    "bilateral", "minister says", "foreign ministry",
    "g7 summit", "g20 summit", "peace summit", "climate summit", "summit meeting",
    "summit ends", "summit begins", "summit concludes", "summit leaders",
]
ID_HINT_WORDS = [
    "yang", "dengan", "untuk", "dalam", "akan", "presiden", "indonesia",
    "jakarta", "pemerintah", "sehingga", "karena", "oleh", "para",
]

GAME_KW = [
    "game", "gaming", "video game", "games", "gameplay", "gamer", "gamertag",
    "gamepass", "game pass", "dlc", "expansion pass", "early access", "battle pass",
    "season pass", "playstation", "ps5", "ps4", "ps6", "xbox", "nintendo",
    "switch 2", "nintendo switch", "steam deck", "steam", "epic games",
    "gta", "grand theft auto", "call of duty", "assassin's creed", "assassins creed",
    "elder ring", "elden ring", "dark souls", "minecraft", "fortnite", "valorant",
    "genshin", "pokemon", "pokémon", "dragon quest", "final fantasy", "resident evil",
    "cyberpunk", "apex legends", "overwatch", "counter-strike", "dota 2",
    "league of legends", "the witcher", "hollow knight", "silksong", "ghost of yotei",
    "black myth", "wukong", "hogwarts legacy", "stardew valley", "balatro",
    "cyberpunk 2077", "red dead redemption", "red dead", "god of war", "horizon zero dawn",
    "ghost of tsushima", "marvel's spiderman", "spiderman", "batman", "superman",
    "gta vi", "witcher 4", "no man's sky", "destiny 2", "path of exile",
    "diablo", "starfield", "kingdom come", "death stranding", "control remastered",
    "ghostrunner", "sifu", "tekken", "street fighter", "mortal kombat", "tekken 8",
    "sonic", "mario", "zelda", "legend of zelda", "metroid", "paper mario",
    "kirby", "animal crossing", "splatoon", "fire emblem", "persona 5",
    "release date", "coming to", "early review", "game awards", "the game awards",
    "rilis game", "rilis", "game baru", "game/download", "gamedev", "game studio",
    "game engine", "game physical", "game digital", "game trailer", "gameplay video",
]

ESPORTS_KW = [
    "esports", "e-sports", "esport", "tournament", "turnamen", "grand slam",
    "roster", "playoffs", "play-off", "quarterfinal", "semifinal", "final match",
    "grand final", "championship", "group stage", "lan final", "co-stream",
    "standings", "seeded", "scrim", "the international", "worlds 2026",
    "esports world cup", "valorant champions", "cs2 ", "counter-strike 2",
    "blast premier", "blast open", "blast tv", "match point", "bracket",
    "lck match", "lck standings", "lpl match", "lec spring", "lec playoffs",
    "msi finals", "vct masters", "vct champions",
]

REVIEW_KW = [
    "review", "ulasan", "hands-on", "hands on", "impressions", "verdict",
    "roundup", "review score", "early review", "scored a", "8/10", "9/10",
    "10/10", "7/10", "6/10", "5/10", "4/10", "worth buying", "worth your money",
    "is it worth", "should you buy", "penilaian", "rekomendasi game", "beli game",
]

HARDWARE_KW = [
    "gpu", "graphics card", "video card", "rtx", "geforce", "radeon", "nvidia",
    "intel arc", "cpu", "processor", "ryzen", "threadripper", "snapdragon",
    "vram", "ddr5", "ddr4", "ssd", "nvme", "pcie", "ray tracing",
    "dlss", "fsr", "fidelity fx", "frame rate", "framerate", "fps", "refresh rate",
    "4k 120", "4k 60", "1080p", "benchmark", "benchmarks", "benchmarking",
    "handheld", "steampad", "steam frame", "consol", "handheld pc",
    "laptop gaming", "gaming laptop", "gaming monitor", "controller", "dualsense",
    "joycon", "joy-con", "haptic", "mouse", "keyboard", "webcam", "headset",
    "thermals", "thermal", "throttling", "power consumption", "latency",
    "60 fps", "120 fps", "144 hz", "240 hz", "240hz", "4k gaming",
    "suhu", "kipas", "pendinginan", "next gen", "next-gen",
    "nextgen", "project helix", "silicon", "wafer", "foundry",
]

# --- Genre game ---
# Genre bisa muncul lebih dari satu (mis. "Elden Ring" = RPG + ACTION +
# OPEN_WORLD). Dua daftar per genre: KW = istilah umum (risiko noise),
# TITLES = judul game spesifik (dipakai kalau KW tidak kena).
GENRES = [
    ("RPG", "RPG", "#c084fc",
     ["rpg", "role-playing", "role playing", "jrpg", "crpg", "mmorpg", "grind",
      "leveling", "character build", "skill tree"],
     ["genshin", "wuthering waves", "honkai star rail", "zenless zone zero",
      "blue archive", "persona 5", "final fantasy", "elden ring", "baldur's gate",
      "skyrim", "divinity original sin", "path of exile", "diablo", "terraria",
      "stardew valley", "nier", "chrono trigger"]),
    ("FPS", "FPS / Shooter", "#f87171",
     ["fps", "shooter", "gunplay", "aim assist", "hitscan", "spray", "loadout"],
     ["call of duty", "battlefield", "counter-strike", "cs2", "team fortress",
      "halo infinite", "master chief", "doom", "metro exodus", "half-life",
      "far cry", "titanfall", "rainbow six"]),
    ("TACTICAL", "Tactical", "#fb7185",
     ["tactical shooter", "tactical fps", "turn-based tactics", "grand tactics",
      "swat", "door breach", "xcom", "wargame", "squad-based"],
     ["rainbow six", "xcom", "ready or not", "total war", "door knockers",
      "insurgency", "helldivers"]),
    ("BATTLE_ROYALE", "Battle Royale", "#f472b6",
     ["battle royale", "last circle", "drop zone", "battlegrounds", "triple kill"],
     ["apex legends", "fortnite", "pubg", "warzone", "naraka", "super battle royale"]),
    ("MOBA", "MOBA", "#e879f9",
     ["moba", "multiplayer online battle arena", "mid lane", "top lane", "bot lane",
      "gank", "5v5", "three-lane", "tower defense game"],
     ["league of legends", "dota 2", "mobile legends", "honor of kings",
      "arena of valor", "marvel rivals", "smite", "wild rift"]),
    ("MMORPG", "MMO", "#818cf8",
     ["mmorpg", "mmo", "massively multiplayer", "server population", "open world mmo"],
     ["world of warcraft", "final fantasy xiv", "guild wars 2", "lost ark",
      "black desert", "new world", "old school runescape", "runescape"]),
    ("STRATEGY", "Strategy", "#38bdf8",
     ["real-time strategy", "rts", "4x", "grand strategy", "base building",
      "tower defense", "auto battler", "city builder", "strategy game"],
     ["starcraft 2", "age of empires", "civilization 7", "into the breach",
      "kingdom rush", "bloons td", "frostpunk", "sins of a solar empire"]),
    ("SURVIVAL", "Survival", "#4ade80",
     ["survival game", "survival crafting", "crafting survival", "hunger",
      "purge night", "extraction shooter", "extraction game", "base raid"],
     ["don't starve", "valheim", "the long dark", "dayz", "green hell",
      "subnautica", "the forest", "project zomboid"]),
    ("HORROR", "Horror", "#ef4444",
     ["horror", "survival horror", "psychological horror", "jump scare", "creepy",
      "haunted", "zombie", "cursed"],
     ["resident evil", "dead space", "silent hill", "evil dead", "dead by daylight",
      "lethal company", "poppy playtime", "signalis", "outlast", "phasmophobia"]),
    ("ACTION", "Action", "#f59e0b",
     ["action game", "hack and slash", "hack-and-slash", "character action",
      "souls-like", "soulslike", "brawler", "beat em up", "combo system"],
     ["devil may cry", "sekiro", "bayonetta", "dark souls", "god of war",
      "yakuza", "devil may cry 5"]),
    ("ADVENTURE", "Adventure", "#34d399",
     ["adventure game", "story-rich", "narrative adventure", "walking simulator",
      "point and click", "escape room", "visual novel", "interactive movie"],
     ["life is strange", "the last of us", "uncharted", "firewatch", "oxenfree",
      "heavy rain", "telltale"]),
    ("OPEN_WORLD", "Open World", "#a3e635",
     ["open world", "open-world", "free roam", "sandbox rpg", "large map"],
     ["breath of the wild", "tears of the kingdom", "witcher 3", "red dead redemption",
      "gta", "grand theft auto", "elden ring", "skyrim", "dragon's dogma", "horizon zero dawn"]),
    ("ROGUELIKE", "Roguelike", "#a78bfa",
     ["roguelike", "roguelite", "rogue-like", "rogue-lite", "run-based",
      "permadeath", "procedural dungeon", "deckbuilder", "deck-builder"],
     ["hades 2", "balatro", "slay the spire", "dead cells", "risk of rain 2",
      "vampire survivors", "brotato", "binding of isaac", "noita"]),
    ("PLATFORMER", "Platformer", "#facc15",
     ["platformer", "platform game", "2d platform", "sidescroller",
      "side-scroller", "precision platforming", "jump and run"],
     ["super mario", "sonic", "celeste", "hollow knight", "crash bandicoot",
      "cuphead", "rayman", "nuclear throne"]),
    ("FIGHTING", "Fighting", "#fb923c",
     ["fighting game", "versus fighter", "frame trap", "combo", "1v1 fighter",
      "fighting roster", "local multiplayer"],
     ["tekken", "street fighter", "mortal kombat", "guilty gear", "fatal fury",
      "marvel vs capcom", "granblue fantasy versus", "brawlhalla"]),
    ("SPORTS", "Sports", "#2dd4bf",
     ["football game", "soccer game", "sports game", "basketball game",
      "tennis game", "ufc", "mma game", "sports simulation", "eFootball"],
     ["ea sports fc", "efootball", "fc 26", "nba 2k", "rock league", "wwe 2k",
      "ufc 5", "just dance"]),
    ("RACING", "Racing", "#f97316",
     ["racing game", "racing", "time trial", "drift", "drifting", "lap time",
      "grand prix", "nascar", "formula 1", "kart racer", "sim racing"],
     ["gran turismo", "forza horizon", "forza motorsport", "need for speed",
      "mario kart", "dirt rally", "f1 ", "wrc", "expeditions"]),
    ("SIMULATION", "Simulation", "#5eead4",
     ["simulator", "simulation game", "life sim", "life simulator", "farming sim",
      "farming simulator", "management sim", "tycoon", "vehicle simulation",
      "flight simulator", "logistics", "power grid"],
     ["stardew valley", "the sims 4", "cities: skylines", "two point hospital",
      "factorio", "planet zoo", "power grid", "the long dark", "farming simulator"]),
    ("PUZZLE", "Puzzle", "#f0abfc",
     ["puzzle game", "puzzle", "match-3", "match 3", "tile matching",
      "physics puzzle", "word game", "sudoku", "casual game", "brain teaser"],
     ["candy crush", "tetris", "sudoku", "monument valley", "the witness",
      "portal 2", "baba is you", "professor layton"]),
    ("CARD_GACHA", "Card / Gacha", "#fb6f9c",
     ["gacha", "gacha game", "card game", "collectible card", "tcg",
      "deck-building", "summon", "banner", "pull rate", "power spike"],
     ["genshin", "honkai star rail", "zenless zone zero", "marvel snap",
      "clash royale", "hearthstone", "yu-gi-oh", "pokemon tcg", "shadowverse"]),
    ("SANDBOX", "Sandbox", "#7dd3fc",
     ["sandbox game", "sandbox", "creative mode", "building game", "voxel",
      "sculpting", "sandbox mode"],
     ["minecraft", "terraria", "roblox", "fortnite creative", "lego worlds",
      "starbound", "eco"]),
    ("METROIDVANIA", "Metroidvania", "#d8b4fe",
     ["metroidvania", "metroid vania", "exploration platformer", "backtracking"],
     ["hollow knight", "metroid dread", "castlevania", "ender lilies",
      "animal well", "axiom of choice", "nine chapters"]),
    ("RHYTHM", "Rhythm", "#bae6fd",
     ["rhythm game", "rhythm", "music game", "note chart", "chart difficulty",
      "song library", "osu!"],
     ["beat saber", "osu!", "clone hero", "rhythm doctor", "guitar hero",
      "just dance", "arcaea"]),
]

GENRE_CODES = [g[0] for g in GENRES]


def norm_title(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_id(title):
    return hashlib.md5(norm_title(title).encode("utf-8")).hexdigest()[:12]


def parse_rfc822(s):
    if not s:
        return None
    try:
        d = eut.parsedate_to_datetime(s)
        if d is None:
            return None
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def parse_date(s):
    """RSS pakai RFC 822, Atom/YouTube & JSON Steam pakai ISO 8601."""
    if not s:
        return None
    d = parse_rfc822(s)
    if d is not None:
        return d
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        d = dt.datetime.fromisoformat(t)
    except Exception:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


ATOM_NS = "{http://www.w3.org/2005/Atom}"
MEDIA_NS = "{http://search.yahoo.com/mrss/}"

FEED_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}


def clean_desc(text, minimum=45, limit=150):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = htmllib.unescape(text).strip()
    if len(text) < minimum or text.lower().startswith(
            ("read more", "http", "untuk selengkapnya")):
        return ""
    return re.sub(r"\s+", " ", text)[:limit]


def make_item(src, src_name, title, link, desc, pub):
    return {
        "title": title,
        "url": link,
        "source": src_name,
        "country": src.get("country", ""),
        "lang": src.get("lang", ""),
        "topic": src.get("topic"),
        "genre": src.get("genre"),
        "boost": int(src.get("boost") or 0),
        "published": pub.isoformat() if pub else None,
        "pub_ts": pub.timestamp() if pub else None,
        "desc": desc,
    }


def parse_rss(root, src):
    out = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        src_name = src["name"]
        sel = it.find("source")
        if sel is not None and (sel.text or "").strip():
            src_name = (sel.text or "").strip()
        if title.endswith(" - " + src_name):
            title = title[: -(len(src_name) + 3)].strip()
        out.append(make_item(src, src_name, title, link,
                             clean_desc(it.findtext("description")),
                             parse_date(it.findtext("pubDate"))))
    return out


def parse_atom(root, src):
    """YouTube (dan feed Atom lain) memakai <entry>, bukan <item>."""
    out = []
    for it in root.findall(".//" + ATOM_NS + "entry"):
        title = (it.findtext(ATOM_NS + "title") or "").strip()
        link = ""
        for lk in it.findall(ATOM_NS + "link"):
            if lk.get("rel") in (None, "alternate") and lk.get("href"):
                link = lk.get("href").strip()
                break
        if not title or not link:
            continue
        if "/shorts/" in link:
            continue
        desc = it.findtext(MEDIA_NS + "group/" + MEDIA_NS + "description") or ""
        if not desc:
            desc = it.findtext(ATOM_NS + "summary") or ""
        out.append(make_item(src, src["name"], title, link,
                             clean_desc(desc),
                             parse_date(it.findtext(ATOM_NS + "published"))))
    return out


def fetch_steam(src):
    """ISteamNews/GetNewsForApp/v2 — API resmi Steam, isi paling cepat."""
    url = ("https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid="
           + str(src["appid"]) + "&count=" + str(src.get("count", 5))
           + "&maxlength=400&feed=steam_announcements")
    req = urllib.request.Request(url, headers=FEED_HEADERS)
    data = json.loads(urllib.request.urlopen(req, timeout=8).read().decode("utf-8"))
    out = []
    for it in data.get("appnews", {}).get("newsitems", []):
        title = (it.get("title") or "").strip()
        if not title:
            continue
        ts = it.get("date") or 0
        pub = dt.datetime.fromtimestamp(ts, dt.timezone.utc) if ts else None
        label = (src.get("label") or src["name"]).strip()
        link = "https://store.steampowered.com/news/app/" + str(src["appid"])
        out.append(make_item(src, label, title, link,
                             clean_desc(it.get("contents"), 60), pub))
    return out


def fetch_feed(src):
    if src.get("kind") == "steam":
        return fetch_steam(src)
    req = urllib.request.Request(src["url"], headers=FEED_HEADERS)
    raw = urllib.request.urlopen(req, timeout=8).read()
    root = ET.fromstring(raw)
    if root.findall(".//" + ATOM_NS + "entry"):
        return parse_atom(root, src)
    return parse_rss(root, src)


def detect_lang(text):
    t = text.lower()
    hits = sum(1 for w in ID_HINT_WORDS if w in t.split())
    return "id" if hits >= 1 else "en"


def count_kw(title, kws):
    return sum(1 for k in kws if k in title)


_KW_BOUNDARY = {}


def kw_word(text, k):
    """Cocok sebagai kata utuh, bukan potongan kata. Tanpa ini "rts" ikut
    cocok di "eSports" dan "eco" ikut cocok di "Economic", sehingga artikel
    non-game ikut bertag genre."""
    rx = _KW_BOUNDARY.get(k)
    if rx is None:
        rx = re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", re.I)
        _KW_BOUNDARY[k] = rx
    return rx.search(text) is not None


def count_genre_kw(text, kws):
    # Pengecekan substring dulu (murah), regex hanya jalan kalau ada kandidat.
    return sum(1 for k in kws if k in text and kw_word(text, k))


def detect_genres(text):
    """Genre bisa lebih dari satu. Skor = jumlah judul game + 2x jumlah
    istilah umum, biar judul game (spesifik) menang dari kata umum."""
    hits = []
    for code, _label, _color, kws, titles in GENRES:
        s = 2 * count_genre_kw(text, kws) + count_genre_kw(text, titles)
        if s > 0:
            hits.append((code, s))
    hits.sort(key=lambda x: -x[1])
    return [c for c, _ in hits]


def game_category(topic, g, es, rv, hw):
    """Pilih sub-kategori game. Untuk sumber bertopic game, tiap kata kunci
    sub-kategori langsung menang karena isinya sudah pasti game.
    Untuk sumber umum, harus menang telak dari kata kunci game inti."""
    core = max(1, g)
    strict = topic is None
    if rv > 0 and (not strict or rv * 2 >= core):
        return "REVIEW_GAME"
    if es > 0 and (not strict or es * 2 >= core):
        return "ESPORTS"
    if hw > 0 and (not strict or hw * 2 >= core):
        return "HARDWARE"
    if topic == "esports":
        return "ESPORTS"
    return "GAME"


def keyword_classify(arts):
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    for a in arts:
        # Nama ikut dinilai: "Eurogamer Reviews" memperkuat deteksi review,
        # "Nintendo of America" memicu kata kunci game.
        t = (a["title"] + " " + (a.get("source") or "")).lower()
        topic = a.get("topic")
        # Nama sumber yang berbentuk domain ("mmorpg.com", "platformer.news")
        # bukan sinyal genre: yangenyebut cuma nama situsnya, bukan isi berita.
        src = a.get("source") or ""
        if "." in src and " " not in src:
            src = ""
        a["genres"] = detect_genres((a["title"] + " " + src).lower())
        src_genre = a.get("genre")
        if src_genre:
            # Feed genre: kalau judulnya tidak cocok genrenya, itu noise dari
            # query Google News — buang, jangan tampilkan.
            if src_genre not in a["genres"]:
                a["drop"] = True
                continue
            a["genres"] = [src_genre] + [x for x in a["genres"] if x != src_genre]
        a["genre_main"] = a["genres"][0] if a.get("genres") else None
        g = count_kw(t, GAME_KW)
        es = count_kw(t, ESPORTS_KW)
        rv = count_kw(t, REVIEW_KW)
        hw = count_kw(t, HARDWARE_KW)
        gg = count_kw(t, GENTING_KW)
        tr = count_kw(t, TRADER_KW)
        pi = count_kw(t, POL_ID_KW)
        pe = count_kw(t, POL_INT_KW)
        lang = a.get("lang") or detect_lang(a["title"])
        recency = 0
        if a.get("pub_ts"):
            age_h = (now - a["pub_ts"]) / 3600.0
            if age_h <= 1:
                recency = 18
            elif age_h <= 6:
                recency = 10
            elif age_h <= 24:
                recency = 4
        base = 32
        cat = "LAINNYA"

        if topic == "hardware":
            if rv > 0:
                cat = "REVIEW_GAME"
                base = 46 + rv * 10 + hw * 6
            elif g > 0 and hw == 0:
                cat = game_category(None, g, es, rv, hw)
                base = 46 + g * 8
            else:
                cat = "HARDWARE"
                base = 46 + hw * 8 + g * 4
        elif topic == "game":
            cat = game_category(topic, g, es, rv, hw)
            base = 44 + g * 6 + max(es, rv, hw) * 10
        elif topic == "esports":
            cat = "ESPORTS"
            base = 50 + es * 10 + g * 5
        elif gg > 0:
            cat = "GENTING"
            base = 55 + gg * 12
        elif tr > 0:
            cat = "TRADER"
            base = 45 + tr * 9
        elif g >= 2 and g * 2 >= (pi + pe):
            cat = game_category(None, g, es, rv, hw)
            base = 38 + g * 6
        elif lang == "id" and pi > 0:
            cat = "POLITIK_ID"
            base = 40 + pi * 8
        elif pe > 0:
            cat = "POLITIK_INT"
            base = 40 + pe * 8
        elif lang == "id":
            cat = "POLITIK_ID"
            base = 34
        else:
            cat = "POLITIK_INT" if pe > 0 else "LAINNYA"
            base = 30 + pe * 8

        base += recency
        base += a.get("boost", 0)
        base = max(10, min(100, int(base)))
        a["category"] = cat
        a["hotness"] = base


def merge_cluster_boost(arts):
    groups = {}
    for a in arts:
        key = norm_title(a["title"])[:40]
        groups.setdefault(key, []).append(a)
    for members in groups.values():
        if len(members) > 1:
            boost = min(15, (len(members) - 1) * 6)
            for m in members:
                m["hotness"] = min(100, m["hotness"] + boost)


def collect_all():
    raw = {}
    ok, fail = [], []
    # 62 sumber, tapi jangan bombardir YouTube/Google sekaligus
    with cf.ThreadPoolExecutor(max_workers=40) as ex:
        futs = {ex.submit(fetch_feed, s): s for s in SOURCES}
        for fut in cf.as_completed(futs):
            s = futs[fut]
            try:
                items = fut.result()
                ok.append(s["name"])
                for it in items:
                    key = norm_title(it["title"])[:60]
                    if not key:
                        continue
                    if key in raw:
                        exst = raw[key]
                        exst["sources"].append(it["source"])
                        if not exst["desc"] and it["desc"]:
                            exst["desc"] = it["desc"]
                        if exst.get("topic") != it.get("topic") and it.get("topic"):
                            exst["topic"] = it["topic"]
                        continue
                    it["id"] = title_id(it["title"])
                    it["sources"] = [it["source"]]
                    raw[key] = it
            except Exception as e:
                fail.append(s["name"] + " (" + str(e)[:40] + ")")
    arts = list(raw.values())
    arts.sort(key=lambda a: a.get("pub_ts") or 0, reverse=True)
    arts = arts[:MAX_ARTICLES * 8]
    for a in arts:
        a["source_main"] = a["sources"][0] if a["sources"] else a["source"]
        a["source_count"] = len(a["sources"])
    return arts, ok, fail


def balance_categories(arts):
    """Pangkas artikel dengan giliran (round-robin) supaya feed game yang
    rame tidak menyingkirkan berita politik, dan sebaliknya.

    Dua tahap:
      1. Kategori non-game (Genting/Politik/Trader/Lainnya) mendapat jatah
         dulu, giliran antar kategori.
      2. Kategori game memakai giliran per genre utama (bukan per kategori),
         supaya genre yang punya sedikit berita - Strategy, Simulation -
         tetap punya isinya. Plafon per kategori game tetap dijaga.

    Article paling panas di tiap kelompok selalu ikut, urutan akhir tetap
    berdasarkan hotness.
    """
    game_groups = {}
    other_groups = {}
    for a in arts:
        cat = a["category"]
        if cat in GAME_CATS:
            key = a.get("genre_main") or "-"
            game_groups.setdefault(key, []).append(a)
        else:
            other_groups.setdefault(cat, []).append(a)
    for group in (game_groups, other_groups):
        for items in group.values():
            items.sort(key=lambda a: -a["hotness"])

    game_budget = int(MAX_ARTICLES * 0.66)
    other_budget = MAX_ARTICLES - game_budget
    kept = []
    cat_count = {}

    i = 0
    while len(kept) < other_budget:
        added = False
        for cat in sorted(other_groups):
            if i >= len(other_groups[cat]):
                continue
            if len(kept) >= other_budget:
                break
            kept.append(other_groups[cat][i])
            cat_count[cat] = cat_count.get(cat, 0) + 1
            added = True
        if not added:
            break
        i += 1

    i = 0
    while len(kept) < MAX_ARTICLES:
        added = False
        for key in sorted(game_groups):
            if i >= len(game_groups[key]):
                continue
            a = game_groups[key][i]
            cat = a["category"]
            if cat_count.get(cat, 0) >= MAX_PER_CAT:
                continue
            if len(kept) >= MAX_ARTICLES:
                break
            kept.append(a)
            cat_count[cat] = cat_count.get(cat, 0) + 1
            added = True
        if not added:
            break
        i += 1

    kept.sort(key=lambda a: -a["hotness"])
    return kept


def build_state():
    arts, ok, fail = collect_all()
    keyword_classify(arts)
    arts = [a for a in arts if not a.get("drop")]
    merge_cluster_boost(arts)
    arts = balance_categories(arts)
    arts.sort(key=lambda a: (-a["hotness"], -(a.get("pub_ts") or 0)))
    articles = [
        {
            "id": a["id"],
            "title": a["title"],
            "title_id": None,
            "url": a["url"],
            "source": a["source_main"],
            "source_count": a.get("source_count", 1),
            "country": a["country"],
            "lang": a.get("lang", ""),
            "category": a["category"],
            "hotness": a["hotness"],
            "genres": a.get("genres") or [],
            "published": a.get("published"),
            "desc": a.get("desc", ""),
        }
        for a in arts
    ]
    return {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "brain": "keyword",
        "provider": None,
        "translate_engine": "browser",
        "note": "Klasifikasi kata kunci. Terjemahan memakai fitur bawaan browser.",
        "refreshing": False,
        "next_refresh_ts": time.time() + 300,
        "sources_ok": ok,
        "sources_fail": fail,
        "categories": [{"code": c[0], "label": c[1], "color": c[2]} for c in CATS],
        "genres": [{"code": g[0], "label": g[1], "color": g[2]} for g in GENRES],
        "articles": articles,
    }


def respond(start_response, code, body, extra_headers=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(data))),
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type"),
        ("Cache-Control", "public, s-maxage=120, stale-while-revalidate=300"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    start_response(str(code) + " OK", headers)
    return [data]


def app(environ, start_response):
    path = (environ.get("PATH_INFO") or "/").rstrip("/") or "/"

    if environ.get("REQUEST_METHOD") == "OPTIONS":
        return respond(start_response, 204, {})

    if path in ("/", "/index.html"):
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        try:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            with open(os.path.join(root, "index.html"), "rb") as f:
                return [f.read()]
        except Exception:
            return [b"<h1>index.html tidak ditemukan</h1>"]

    if path == "/api/news" or path == "/api/status":
        try:
            return respond(start_response, 200, build_state())
        except Exception as e:
            return respond(start_response, 200, {
                "updated_at": None,
                "brain": "error",
                "provider": None,
                "translate_engine": "browser",
                "note": "Gagal mengambil berita: " + str(e)[:120],
                "refreshing": False,
                "next_refresh_ts": time.time() + 60,
                "sources_ok": [],
                "sources_fail": [str(e)[:120]],
                "categories": [{"code": c[0], "label": c[1], "color": c[2]} for c in CATS],
                "genres": [{"code": g[0], "label": g[1], "color": g[2]} for g in GENRES],
                "articles": [],
            })

    if path == "/api/health":
        return respond(start_response, 200, {"ok": True, "service": "news-api"})

    start_response("404 Not Found", [("Content-Type", "application/json")])
    return [b'{"error":"not found"}']
