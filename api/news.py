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
    ("BOLA", "Sepak Bola", "#34d399"),
    ("BOLA_LIGA", "Liga & Kompetisi", "#818cf8"),
    ("BOLA_TRANSFER", "Transfer", "#fb923c"),
    ("BOLA_NASIONAL", "Timnas & Liga 1", "#e879f9"),
    ("CYBER_VULN", "Kerentanan & CVE", "#facc15"),
    ("CYBER_MALWARE", "Malware & Ransomware", "#ef4444"),
    ("CYBER_APT", "Threat Intel & APT", "#a855f7"),
    ("CYBER_BREACH", "Kebocoran Data", "#f472b6"),
    ("CYBER_BUG", "Bug Bounty & Pentest", "#c084fc"),
    ("CYBER_TOOL", "Tool Offensive & Red Team", "#22d3ee"),
    ("CYBER_BLUE", "Blue Team / DFIR / SOC", "#38bdf8"),
    ("CYBER_CLOUD", "Cloud & Container", "#2dd4bf"),
    ("CYBER_APP", "AppSec & Web", "#4ade80"),
    ("CYBER_RE", "Reverse Engineering", "#fb923c"),
    ("CYBER_AI", "AI Security", "#818cf8"),
    ("CYBER_GRC", "Regulasi & GRC", "#94a3b8"),
    ("POLITIK_ID", "Politik Dalam Negeri", "#4da6ff"),
    ("POLITIK_INT", "Politik Internasional", "#8a6dff"),
    ("TRADER", "Trader / Pasar", "#ffc14d"),
    ("LAINNYA", "Lainnya", "#7a8290"),
]

# Kategori yang hanya boleh diisi oleh sumber bertopic game
GAME_CATS = ["GAME", "ESPORTS", "REVIEW_GAME", "HARDWARE"]
# Kategori yang hanya boleh diisi oleh sumber bertopic bola
BOLA_CATS = ["BOLA", "BOLA_LIGA", "BOLA_TRANSFER", "BOLA_NASIONAL"]
# Kategori yang hanya boleh diisi oleh sumber bertopic cyber
CYBER_CATS = ["CYBER_VULN", "CYBER_MALWARE", "CYBER_APT", "CYBER_BREACH",
              "CYBER_BUG", "CYBER_TOOL", "CYBER_BLUE", "CYBER_CLOUD",
              "CYBER_APP", "CYBER_RE", "CYBER_AI", "CYBER_GRC"]

# Porsi jatah artikel akhir tiap keluarga topik. Tanpa ini, keluarga dengan
# sumber paling rame akan memakan seluruh kuota dan tab lain kosong.
# Cyber dapat porsi besar karena 12 bidang harus tetap terisi.
FAMILY_SHARE = {"other": 0.10, "game": 0.24, "bola": 0.24, "cyber": 0.42}


def family_of(cat):
    if cat in GAME_CATS:
        return "game"
    if cat in BOLA_CATS:
        return "bola"
    if cat in CYBER_CATS:
        return "cyber"
    return "other"


# Batas jumlah artikel akhir per kategori supaya tiap tab berisi.
# 23 genre + 4 tab bola + 12 tab cyber harus tetap punya isinya setelah
# pengimbangan, jadi kuota total dinaikkan dan plafon per kategori dilonggarkan.
MAX_ARTICLES = 960
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

# =====================================================================
# BERITA SEPAK BOLA (Indonesia + internasional)
# =====================================================================
# Hampir semua klub besar TIDAK punya RSS publik (dihapus atau 403), jadi
# tiga lapis sumber dipakai:
#   1. Media yang RSS-nya benar-benar hidup dan sudah diuji.
#   2. Channel YouTube resmi klub/liga/pemain (first-party, paling cepat).
#   3. Google News per subjek, supaya klub besar dan pemain individu tetap
#      ter-covered walau tidak punya feed sendiri.

# --- 1. Media (semua diuji hidup) ---
BOLA_MEDIA = [
    ("BBC Football", "https://feeds.bbci.co.uk/sport/football/rss.xml", "WORLD", "en", 12),
    ("The Guardian Football", "https://www.theguardian.com/football/rss", "WORLD", "en", 12),
    ("90min", "https://www.90min.com/posts.rss", "WORLD", "en", 10),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040", "WORLD", "en", 11),
    ("Yahoo Soccer", "https://sports.yahoo.com/soccer/rss", "WORLD", "en", 9),
    ("Standard Football", "https://www.standard.co.uk/sport/football/rss", "WORLD", "en", 10),
    ("Kicker", "https://newsfeed.kicker.de/news/aktuell", "WORLD", "de", 10),
    ("Planet Football", "https://www.planetfootball.com/feed/", "WORLD", "en", 8),
    ("Bundesliga", "https://www.bundesliga.com/en/bundesliga/news/rss", "WORLD", "en", 12),
    ("CNN Indonesia", "https://www.cnnindonesia.com/rss", "ID", "id", 8),
    ("detikSport", "https://sport.detik.com/rss", "ID", "id", 8),
    ("Sindonews", "https://www.sindonews.com/rss/Sport", "ID", "id", 7),
    ("Tribun", "https://www.tribunnews.com/rss", "ID", "id", 7),
    ("Nusantara Post", "https://nusantarapost.id/feed/", "ID", "id", 6),
]

# --- 2. YouTube resmi (channel_id diverifikasi lewat halaman channel,
#        bukan hasil tebakan; tiap baris hanya yang nama channel aslinya
#        cocok - mis. @AVWC bukan Aston Villa, @LaLiga bukan Liga resmi) ---
BOLA_CHANNELS = [
    ("FIFA", "UCpcTrCXblq78GZrTUTLWeBw", 14),
    ("UEFA", "UCyGa1YEx9ST66rYrJTGIKOw", 14),
    ("Premier League", "UCG5qGWdu8nIRZqJ_GgDwQ-w", 13),
    ("Serie A", "UCBJeMCIeLQos7wacox4hmLQ", 13),
    ("Ligue 1", "UCQsH5XtIc9hONE1BQjucM0g", 12),
    ("Bundesliga", "UC6UL29enLNe4mqwTfAyeNuw", 12),
    ("Liverpool FC", "UC9LQwHZoucFT94I2h6JOcjw", 13),
    ("Arsenal", "UCpryVRk_VDudG8SHXgWcG0w", 13),
    ("Manchester United", "UC6yW44UGJJBvYTlfC7CRg2Q", 13),
    ("Real Madrid", "UCWV3obpZVGgJ3j9FVhEjF2Q", 13),
    ("FC Barcelona", "UC14UlmYlSNiQCBe9Eookf_A", 13),
    ("Juventus", "UCLzKhsxrExAC6yAdtZ-BOWw", 13),
    ("Inter", "UCvXzEblUa0cfny4HAJ_ZOWw", 13),
    ("Tottenham", "UCEg25rdRZXg32iwai6N6l0w", 13),
    ("Chelsea", "UCU2PacFf99vhb3hNiYDmxww", 13),
    ("Borussia Dortmund", "UCK8rTVgp3-MebXkmeJcQb1Q", 12),
    ("FC Bayern", "UCZkcxFIsqW5htimoUQKA0iA", 13),
    ("Paris Saint-Germain", "UCt9a_qP9CqHCNwilf-iULag", 13),
    ("Ajax", "UCGpf7WX7R1one-NwOvg_PbQ", 11),
    ("Celtic", "UCBN-bb-hE7jYlcp4exwXRsQ", 11),
    ("Newcastle", "UCywGl_BPp9QhD0uAcP2HsJw", 12),
    ("Nottingham Forest", "UCyAxjuAr8f_BFDGCO3Htbxw", 12),
    ("AS Roma", "UCLttSYJ6kPtlcurY96kXkQw", 12),
    ("Feyenoord", "UCg_DGzRRIQlXpHxCrMMiAIQ", 11),
    ("Sevilla FC", "UCLy9lmj_0cqffXUzbGHNmYA", 11),
    ("Galatasaray", "UCQpeujIamj2ZOKXZnrxTRhA", 11),
    ("Al Ahly", "UCA86pBGxVPZGrTeTecOtjew", 11),
    ("Al Nassr", "UCTgtmWmcSm21GLcFYwkfXvA", 11),
]

# --- 3. Google News per subjek ---
# Query pakai when:7d supaya isinya benar-benar yang terbaru; tanpa itu
# Google News mengembalikan artikel lama yang tak pernah tenggelam.
BOLA_QUERIES = [
    # Indonesia
    ("NASIONAL", "Timnas Indonesia", "Timnas Indonesia OR PSSI", 12),
    ("NASIONAL", "Liga 1 Indonesia", '"Liga 1" OR "Liga 2" Indonesia', 11),
    ("NASIONAL", "Bola Indonesia", '"Liga Indonesia" OR "sepak bola Indonesia"', 10),
    ("NASIONAL", "Piala Asia Timnas", '"Piala Asia" OR "ASEAN Cup" Indonesia', 10),
    # Klub Indonesia (per perusahaan)
    ("NASIONAL", "Persib Bandung", '"Persib Bandung"', 11),
    ("NASIONAL", "Persija Jakarta", '"Persija Jakarta"', 11),
    ("NASIONAL", "Persebaya", '"Persebaya"', 10),
    ("NASIONAL", "Arema", '"Arema" OR "Arema FC"', 10),
    ("NASIONAL", "Bali United", '"Bali United"', 10),
    ("NASIONAL", "PSM Makassar", '"PSM Makassar"', 10),
    ("NASIONAL", "Persipura", '"Persipura"', 9),
    ("NASIONAL", "Persela Solo", '"Persela"', 9),
    # Pemain & pelatih Indonesia (per orang)
    ("NASIONAL", "Marselino Ferdinan", '"Marselino Ferdinan"', 10),
    ("NASIONAL", "Jay Idzes", '"Jay Idzes"', 10),
    ("NASIONAL", "Ragnar Oratmangoen", '"Ragnar Oratmangoen" OR "Ragnar"', 9),
    ("NASIONAL", "Justin Hubner", '"Justin Hubner"', 9),
    ("NASIONAL", "Sandy Walsh", '"Sandy Walsh"', 9),
    ("NASIONAL", "Asnawi Miftah", '"Asnawi"', 9),
    # Kompetisi internasional
    ("LIGA", "Liga Champions", '"Liga Champions" OR "Champions League"', 12),
    ("LIGA", "Premier League", '"Premier League"', 12),
    ("LIGA", "La Liga", '"La Liga" OR "Liga BBVA"', 11),
    ("LIGA", "Serie A", '"Serie A" Italia', 11),
    ("LIGA", "Bundesliga", 'Bundesliga', 11),
    ("LIGA", "Ligue 1", '"Ligue 1" OR "French football"', 11),
    ("LIGA", "Piala Dunia 2026", '"World Cup 2026" OR "Piala Dunia 2026"', 12),
    ("LIGA", "Piala Europa", '"Europa League" OR "Conference League"', 10),
    ("LIGA", "Piala Klub Dunia", '"Club World Cup"', 9),
    # Klub besar
    ("BOLA", "Manchester United", '"Manchester United" OR "Man Utd"', 12),
    ("BOLA", "Liverpool", '"Liverpool"', 12),
    ("BOLA", "Real Madrid", '"Real Madrid"', 12),
    ("BOLA", "Barcelona", '"Barcelona" football OR "FC Barcelona"', 12),
    ("BOLA", "Bayern Munich", '"Bayern Munich" OR "Bayern Munchen"', 11),
    ("BOLA", "Inter Milan", '"Inter Milan" OR "Inter de Milan"', 11),
    ("BOLA", "Arsenal", '"Arsenal"', 11),
    ("BOLA", "Chelsea", '"Chelsea"', 10),
    ("BOLA", "PSG", '"Paris Saint-Germain" OR PSG', 11),
    ("BOLA", "Juventus", '"Juventus"', 10),
    # Pemain (per orang)
    ("BOLA", "Cristiano Ronaldo", '"Cristiano Ronaldo" OR CR7', 12),
    ("BOLA", "Lionel Messi", '"Lionel Messi" OR Messi', 12),
    ("BOLA", "Erling Haaland", '"Erling Haaland" OR Haaland', 10),
    ("BOLA", "Mohamed Salah", '"Mohamed Salah"', 10),
    ("BOLA", "Kylian Mbappe", '"Kylian Mbappe"', 10),
    ("BOLA", "Vinicius Junior", '"Vinicius Junior" OR "Vinicius Juniors"', 10),
    ("BOLA", "Jude Bellingham", '"Jude Bellingham"', 9),
    ("BOLA", "Harry Kane", '"Harry Kane"', 9),
    # Transfer
    ("TRANSFER", "Bursa Transfer", '"transfer" ("Premier League" OR "La Liga" OR Serie A)', 12),
    ("TRANSFER", "Jual Beli Pemain", '"jual beli" pemain OR "rekrut" pemain sepak bola', 11),
]

for _nm, _url, _cc, _lg, _bs in BOLA_MEDIA:
    SOURCES.append({
        "name": _nm, "url": _url, "country": _cc, "lang": _lg,
        "topic": "bola", "boost": _bs,
    })

for _nm, _cid, _bs in BOLA_CHANNELS:
    SOURCES.append({
        "name": "YT " + _nm,
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=" + _cid,
        "kind": "atom", "country": "WORLD", "lang": "en",
        "topic": "bola", "boost": _bs,
    })

for _cat, _nm, _q, _bs in BOLA_QUERIES:
    SOURCES.append({
        "name": "Bola " + _nm,
        "url": "https://news.google.com/rss/search?q="
               + urllib.parse.quote(_q + " when:7d") + "&hl=id&gl=ID&ceid=ID:id",
        "country": "ID", "lang": "id",
        "topic": "bola", "bola_cat": _cat, "boost": _bs,
    })

# ===================================================================
# Keamanan siber
# ===================================================================
# Satu-satunya sumber tool yang benar-benar bisa diandalkan adalah feed
# rilis resmi proyeknya sendiri (GitHub releases.atom). Google News untuk
# query "tool baru" hampir kosong atau noisy, jadi feed rilis resmi proyek
# yang diandalkan; Google News hanya menambah liputan media.

# --- 1. Media & riset (nama, url, kategori, boost) ---
# kategori = None berarti routing per artikel pakai kata kunci (media umum
# yang membahas banyak bidang sekaligus).
CYBER_MEDIA = [
    # Liputan keamanan harian (umum, routing per artikel)
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews", None, 10),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/", None, 10),
    ("SecurityWeek", "https://www.securityweek.com/feed/", None, 9),
    ("The Record", "https://therecord.media/feed", None, 10),
    ("Dark Reading", "https://www.darkreading.com/rss.xml", None, 8),
    ("Help Net Security", "https://www.helpnetsecurity.com/feed/", None, 8),
    ("Security Affairs", "https://securityaffairs.com/feed", None, 8),
    ("Graham Cluley", "https://grahamcluley.com/feed/", None, 8),
    ("Microsoft Security", "https://www.microsoft.com/en-us/security/blog/feed/", None, 8),
    ("Google Security Blog", "https://security.googleblog.com/feeds/posts/default", None, 8),
    ("GitHub Blog", "https://github.blog/feed/", None, 7),
    # Vendor & riset (spesifik satu bidang)
    ("Schneier on Security", "https://www.schneier.com/feed/atom/", "CYBER_GRC", 8),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/", "CYBER_BREACH", 10),
    ("WeLiveSecurity", "https://www.welivesecurity.com/en/rss/feed/", "CYBER_MALWARE", 9),
    ("Securelist", "https://securelist.com/feed/", "CYBER_MALWARE", 9),
    ("Malwarebytes Labs", "https://www.malwarebytes.com/blog/feed/", "CYBER_MALWARE", 9),
    ("Avast Blog", "https://blog.avast.com/feed", "CYBER_MALWARE", 7),
    ("Recorded Future", "https://www.recordedfuture.com/feed", "CYBER_APT", 8),
    ("Red Canary", "https://redcanary.com/blog/feed/", "CYBER_BLUE", 8),
    ("CrowdStrike", "https://www.crowdstrike.com/blog/feed/", "CYBER_APT", 8),
    ("SentinelOne Labs", "https://www.sentinelone.com/labs/feed/", "CYBER_APT", 8),
    ("Horizon3", "https://horizon3.ai/feed/", "CYBER_VULN", 8),
    ("Check Point Research", "https://research.checkpoint.com/feed/", "CYBER_APT", 9),
    ("Unit 42", "https://unit42.paloaltonetworks.com/feed/", "CYBER_APT", 9),
    ("Google Cloud TI", "https://cloudblog.withgoogle.com/topics/threat-intelligence/rss/", "CYBER_APT", 8),
    ("Google Project Zero", "https://googleprojectzero.blogspot.com/feeds/posts/default", "CYBER_VULN", 12),
    ("Chrome Releases", "https://chromereleases.googleblog.com/feeds/posts/default", "CYBER_VULN", 8),
    ("Exploit-DB", "https://www.exploit-db.com/rss.xml", "CYBER_VULN", 10),
    ("Wiz Research", "https://www.wiz.io/blog/rss.xml", "CYBER_CLOUD", 9),
    ("AWS Security Blog", "https://aws.amazon.com/blogs/security/feed/", "CYBER_CLOUD", 8),
    ("Snyk Blog", "https://snyk.io/blog/feed", "CYBER_APP", 8),
    ("PortSwigger Research", "https://portswigger.net/research/rss", "CYBER_APP", 12),
    ("SANS ISC", "https://isc.sans.edu/rssfeed_full.xml", "CYBER_BLUE", 9),
    ("InfoSec Writeups", "https://infosecwriteups.com/feed", "CYBER_BUG", 9),
    ("Hacking Articles", "https://www.hackingarticles.in/feed/", "CYBER_BUG", 9),
    ("Kali Linux News", "https://www.kali.org/feed/", "CYBER_TOOL", 9),
    ("Trail of Bits", "https://blog.trailofbits.com/feed/", "CYBER_RE", 10),
    ("Binarly", "https://www.binarly.io/blog/rss.xml", "CYBER_RE", 9),
    ("ANY.RUN", "https://any.run/cybersecurity-blog/feed/", "CYBER_RE", 9),
    ("Virus Bulletin", "https://www.virusbulletin.com/rss", "CYBER_MALWARE", 8),
    ("MalwareTips", "https://malwaretips.com/forums/-/index.rss", "CYBER_MALWARE", 7),
]

# --- 1b. Media sosial & komunitas (nama, url, kategori, boost) ---
# Mastodon punya RSS resmi per akun (stabil, tanpa API key). X/Twitter,
# Bluesky, TikTok, IG, FB tidak punya RSS resmi -> tidak dipakai.
# `social: True` menandai feed yang isinya pendek/deskripsi = postingan.
CYBER_SOCIAL = [
    ("Mastodon @briankrebs", "https://infosec.exchange/@briankrebs.rss", "CYBER_BREACH", 10),
    ("Mastodon @malwaretech", "https://infosec.exchange/@malwaretech.rss", "CYBER_MALWARE", 10),
    ("Mastodon @SwiftOnSecurity", "https://infosec.exchange/@SwiftOnSecurity.rss", "CYBER_BLUE", 9),
    ("Mastodon @cyb3rops", "https://infosec.exchange/@cyb3rops.rss", "CYBER_BLUE", 9),
    ("Mastodon @thegrugq", "https://infosec.exchange/@thegrugq.rss", "CYBER_APT", 9),
    ("Mastodon @hacks4pancakes", "https://infosec.exchange/@hacks4pancakes.rss", "CYBER_BLUE", 9),
    ("Mastodon @malwarejake", "https://infosec.exchange/@malwarejake.rss", "CYBER_BLUE", 8),
    ("Mastodon @lcamtuf", "https://infosec.exchange/@lcamtuf.rss", "CYBER_VULN", 9),
    ("Mastodon @0xabad1dea", "https://infosec.exchange/@0xabad1dea.rss", "CYBER_APP", 8),
    ("Mastodon @JackRhysider", "https://infosec.exchange/@JackRhysider.rss", "CYBER_MALWARE", 8),
    ("Mastodon @k8em0", "https://infosec.exchange/@k8em0.rss", "CYBER_BUG", 8),
    ("Mastodon @mubix", "https://infosec.exchange/@mubix.rss", "CYBER_TOOL", 8),
    ("Mastodon @ryanaraine", "https://infosec.exchange/@ryanaraine.rss", "CYBER_APT", 8),
    ("Mastodon @mattjay", "https://infosec.exchange/@mattjay.rss", "CYBER_APT", 8),
    # Komunitas link (routing per artikel)
    ("Lobsters Security", "https://lobste.rs/t/security.rss", None, 9),
    ("Lobsters Privacy", "https://lobste.rs/t/privacy.rss", "CYBER_GRC", 8),
    ("HN Security", "https://hnrss.org/newest?q=security&points=10", None, 8),
    ("HN Vulnerability", "https://hnrss.org/newest?q=vulnerability", None, 8),
    ("HN Ransomware", "https://hnrss.org/newest?q=ransomware", None, 8),
    ("HN Reverse Engineering", "https://hnrss.org/newest?q=reverse%20engineering", None, 8),
]

# --- 2. Rilis tool resmi (nama, repo GitHub) ---
# feeds/videos.xml tidak berlaku di sini: GitHub menyediakan releases.atom
# per proyek, isinya persis versi + catatan rilis, dan selalu up-to-date.
CYBER_TOOLS = [
    ("nuclei", "projectdiscovery/nuclei"),
    ("nuclei-templates", "projectdiscovery/nuclei-templates"),
    ("httpx", "projectdiscovery/httpx"),
    ("subfinder", "projectdiscovery/subfinder"),
    ("katana", "projectdiscovery/katana"),
    ("naabu", "projectdiscovery/naabu"),
    ("interactsh", "projectdiscovery/interactsh"),
    ("cloudlist", "projectdiscovery/cloudlist"),
    ("Amass", "owasp-amass/amass"),
    ("ffuf", "ffuf/ffuf"),
    ("Metasploit", "rapid7/metasploit-framework"),
    ("OWASP ZAP", "zaproxy/zaproxy"),
    ("mitmproxy", "mitmproxy/mitmproxy"),
    ("sqlmap", "sqlmapproject/sqlmap"),
    ("nikto", "sullo/nikto"),
    ("chisel", "jpillora/chisel"),
    ("bettercap", "bettercap/bettercap"),
    ("Sliver", "BishopFox/sliver"),
    ("BloodHound", "SpecterOps/BloodHound"),
    ("BBOT", "blacklanternsecurity/bbot"),
    ("Impacket", "fortra/impacket"),
    ("Semgrep", "semgrep/semgrep"),
    ("gitleaks", "gitleaks/gitleaks"),
    ("trufflehog", "trufflesecurity/trufflehog"),
    ("SecLists", "danielmiessler/SecLists"),
    ("PwnDoc", "pwndoc/pwndoc"),
    ("CyberChef", "gchq/CyberChef"),
    ("YARA", "VirusTotal/yara"),
    ("Suricata", "OISF/suricata"),
    ("Volatility", "volatilityfoundation/volatility3"),
    ("Trivy", "aquasecurity/trivy"),
    ("WPScan", "wpscanteam/wpscan"),
    ("Juice Shop", "juice-shop/juice-shop"),
]

# --- 3. YouTube (channel_id sudah diverifikasi lewat halaman channel) ---
CYBER_VIDEOS = [
    ("NetworkChuck", "UC9x0AN7BWHpCDHSm9NiJFJQ", "CYBER_TOOL", 9),
    ("John Hammond", "UCVeW9qkBjo3zosnqUbG7CFw", "CYBER_TOOL", 10),
    ("SecurityNOW", "UCNbqa_9xihC8yaV2o6dlsUg", "CYBER_BLUE", 9),
    ("HackerSploit", "UC0ZTPkdxlAKf-V33tqXwi3Q", "CYBER_TOOL", 10),
    ("Bishop Fox", "UCE8o_Vx1nbvaGf_N0EsIgjg", "CYBER_BUG", 10),
    ("SpecterOps", "UCWMKKqCCQkUjU8dIyiL1yhQ", "CYBER_TOOL", 9),
    ("NCC Group", "UCiWMGVQt1pKZITUmGquSGDQ", "CYBER_VULN", 8),
    ("Assetnote", "UCl9w-WcO9E-XAEtvWWuNPnw", "CYBER_VULN", 9),
    ("NetSPI", "UCHUKizdbC44pUu_vcT5vlTQ", "CYBER_BUG", 10),
    ("David Bombal", "UCP7WmQ_U4GB3K51Od9QvM0w", "CYBER_TOOL", 9),
    ("IppSec", "UCa6eh7gCkpPo5XXUDfygQQA", "CYBER_BUG", 8),
    ("PwnFunction", "UCW6MNdOsqv2E9AjQkv9we7A", "CYBER_APP", 9),
    ("InsiderPhD", "UCPiN9NPjIer8Do9gUFxKv7A", "CYBER_BUG", 8),
    ("Tricentis", "UCqeo7wfzxlv4SS8pJWhOHIQ", "CYBER_TOOL", 7),
    ("LiveOverflow", "UClcE-kVhqyiHCcjYwcpfj9w", "CYBER_RE", 9),
    ("sudo room", "UCe3DiJvItBa_DWWktd-ushA", "CYBER_TOOL", 8),
]

# --- 4. Google News (kategori, nama, query, locale, boost) ---
CYBER_LOC = {"id": "&hl=id&gl=ID&ceid=ID:id", "en": "&hl=en-US&gl=US&ceid=US:en"}
CYBER_QUERIES = [
    # --- kerentanan & CVE ---
    ("CYBER_VULN", "Zero-day", '"zero-day" OR "zero day" exploit', "en", 11),
    ("CYBER_VULN", "Eksploitasi aktif", '"actively exploited" OR "exploited in the wild"', "en", 11),
    ("CYBER_VULN", "Katalog CISA", '"known exploited" OR "added to the catalog"', "en", 10),
    ("CYBER_VULN", "Patch perangkat", '"security update" OR "security patch" OR "security fix" (Chrome OR Windows OR Android OR iOS)', "en", 10),
    ("CYBER_VULN", "Vendor besar", '(Microsoft OR Google OR Apple OR Cisco OR Fortinet OR "Palo Alto") (vulnerability OR "security advisory")', "en", 10),
    ("CYBER_VULN", "Ivanti Citrix", '(Ivanti OR "Connect Secure" OR NetScaler OR Citrix) vulnerability', "en", 10),
    ("CYBER_VULN", "Web & server", '(Apache OR Nginx OR OpenSSH OR "Linux kernel" OR Drupal) (vulnerability OR CVE)', "en", 9),
    ("CYBER_VULN", "Aplikasi bisnis", '(Confluence OR Atlassian OR Salesforce OR SAP OR Oracle) (vulnerability OR CVE)', "en", 9),
    ("CYBER_VULN", "Celah aplikasi ID", 'kerentanan OR "celah keamanan"', "id", 10),
    # --- malware & ransomware ---
    ("CYBER_MALWARE", "Ransomware", '(ransomware OR "data extortion") (campaign OR gang OR attack)', "en", 10),
    ("CYBER_MALWARE", "Infostealer", '(infostealer OR "info stealer" OR "credential stealer")', "en", 9),
    ("CYBER_MALWARE", "Botnet & DDoS", '(botnet OR DDoS OR "denial of service") (campaign OR takedown)', "en", 9),
    ("CYBER_MALWARE", "Trojan & backdoor", '(trojan OR backdoor OR rootkit OR "remote access trojan") (malware OR campaign)', "en", 9),
    ("CYBER_MALWARE", "Ransomware ID", 'ransomware Indonesia', "id", 9),
    # --- threat intel & APT ---
    ("CYBER_APT", "APT & nation-state", '("advanced persistent threat" OR "nation-state" OR "state-sponsored") (campaign OR attribution)', "en", 9),
    ("CYBER_APT", "Threat actor", '("threat actor" OR "threat group" OR "cyber espionage") (campaign OR malware)', "en", 9),
    ("CYBER_APT", "Vendor malware", '(Zimperium OR Kaspersky OR Mandiant OR "Check Point Research") (report OR research OR malware)', "en", 9),
    ("CYBER_APT", "Badan & anjuran", '("CISA" OR ENISA OR "NCSC" OR "CERT-EU") (advisory OR warning OR urges OR report)', "en", 10),
    ("CYBER_APT", "Keamanan siber ID", 'keamanan siber OR serangan siber', "id", 10),
    # --- kebocoran data ---
    ("CYBER_BREACH", "Data breach", '("data breach" OR "database leak" OR "records exposed") (announces OR confirms OR hacked)', "en", 9),
    ("CYBER_BREACH", "Data pribadi bocor", '("personal data" OR "customer data") (leaked OR exposed OR stolen)', "en", 9),
    ("CYBER_BREACH", "Data breach ID", '"data breach" Indonesia', "id", 10),
    ("CYBER_BREACH", "Kebocoran data ID", '"kebocoran data" OR "data bocor"', "id", 9),
    # --- bug bounty & pentest ---
    ("CYBER_BUG", "Bug bounty", '"bug bounty" (program OR payout OR "new program")', "en", 10),
    ("CYBER_BUG", "Platform bounty", '(HackerOne OR Bugcrowd OR YesWeHack OR Intigriti OR Patchstack) (bounty OR disclosure OR announce OR launch)', "en", 10),
    ("CYBER_BUG", "Bounty besar", '("bug bounty" AND (Microsoft OR Google OR Apple OR Meta OR Mozilla)) (payout OR program OR scope)', "en", 10),
    ("CYBER_BUG", "Red team", '("red team" OR "adversary simulation") (findings OR report OR campaign)', "en", 9),
    ("CYBER_BUG", "Bug bounty ID", '"bug bounty" Indonesia', "id", 10),
    ("CYBER_BUG", "Pentest ID", 'pentest OR penetration testing Indonesia', "id", 9),
    # --- tool offensive & red team ---
    ("CYBER_TOOL", "Exploit framework", '("Metasploit" OR "Burp Suite" OR "nuclei" OR "sqlmap" OR "impacket") ("new version" OR "update" OR "release")', "en", 10),
    ("CYBER_TOOL", "C2 & payload", '("C2 framework" OR "C2 server" OR "command-and-control") (malware OR hacking OR "open source")', "en", 9),
    ("CYBER_TOOL", "Fuzzing", '(fuzzing OR fuzzer OR "fuzz target") (tool OR "open source" OR release)', "en", 9),
    ("CYBER_TOOL", "Komunitas offensive", '("SANS" OR "Offensive Security" OR "Hack The Box" OR TryHackMe) (report OR research OR tool OR release)', "en", 9),
    # --- blue team / dfir / soc ---
    ("CYBER_BLUE", "Blue team & DFIR", '("blue team" OR "incident response" OR "digital forensics" OR DFIR) (report OR tool OR technique)', "en", 9),
    ("CYBER_BLUE", "Threat hunting", '("threat hunting" OR "threat detection" OR "detection engineering") (report OR tool OR rule)', "en", 9),
    ("CYBER_BLUE", "Malware defense", '("endpoint detection" OR EDR OR SIEM) (detection OR rule OR report)', "en", 8),
    # --- cloud & container ---
    ("CYBER_CLOUD", "Cloud security", '("cloud security" OR "cloud misconfiguration") (AWS OR Azure OR "Google Cloud" OR Kubernetes)', "en", 9),
    ("CYBER_CLOUD", "Supply chain", '("supply chain attack" OR "third-party breach" OR "update compromise")', "en", 9),
    ("CYBER_CLOUD", "Kubernetes & container", '(Kubernetes OR Docker OR container) (vulnerability OR attack OR security)', "en", 9),
    # --- appsec & web ---
    ("CYBER_APP", "AppSec & OWASP", '(OWASP OR "application security" OR AppSec) (vulnerability OR tool OR report)', "en", 9),
    ("CYBER_APP", "Web security", '("web security" OR XSS OR CSRF OR SSRF) (vulnerability OR attack)', "en", 9),
    ("CYBER_APP", "API security", '("API security" OR "broken access control") (vulnerability OR attack)', "en", 8),
    # --- reverse engineering ---
    ("CYBER_RE", "Reverse engineering", '("reverse engineering" OR Ghidra OR IDA OR "binary analysis") (malware OR firmware OR analysis)', "en", 9),
    ("CYBER_RE", "Malware analysis", '("malware analysis" OR "binary analysis" OR "static analysis") (report OR technique OR tool)', "en", 9),
    ("CYBER_RE", "Disassembler & decompiler", '(Ghidra OR "IDA Pro" OR "Binary Ninja" OR decompiler OR disassembler)', "en", 8),
    ("CYBER_RE", "Firmware reversing", '(firmware OR "reverse engineering") (extraction OR reversing OR unpacking)', "en", 8),
    ("CYBER_RE", "Reverse engineering ID", 'reverse engineering OR "analisis malware"', "id", 8),
    # --- AI security ---
    ("CYBER_AI", "AI security", '("AI security" OR "LLM security" OR "prompt injection") (attack OR vulnerability OR research)', "en", 9),
    ("CYBER_AI", "Ancaman AI", '("AI agent" OR LLM) (attack OR "prompt injection" OR exploitation) security', "en", 9),
    ("CYBER_AI", "Deepfake & model", '(deepfake OR "model poisoning" OR "adversarial machine learning")', "en", 8),
    # --- regulasi & GRC ---
    ("CYBER_GRC", "Regulasi & compliance", '("cybersecurity regulation" OR "cyber regulation" OR "cyber compliance" OR GDPR OR NIS2 OR "ISO 27001" OR "data protection law")', "en", 9),
    ("CYBER_GRC", "Kebijakan keamanan", '("cybersecurity policy" OR "cyber law" OR cybersecurity legislation) (government OR parliament)', "en", 8),
    ("CYBER_GRC", "Regulasi ID", 'regulasi keamanan siber OR "UU PDP" OR "perlindungan data pribadi"', "id", 9),
]

for _nm, _url, _cat, _bs in CYBER_MEDIA:
    SOURCES.append({
        "name": _nm, "url": _url, "country": "WORLD", "lang": "en",
        "topic": "cyber", "cyber_cat": _cat, "boost": _bs,
    })

for _nm, _url, _cat, _bs in CYBER_SOCIAL:
    SOURCES.append({
        "name": _nm, "url": _url, "country": "WORLD", "lang": "en",
        "topic": "cyber", "cyber_cat": _cat, "social": True, "boost": _bs,
    })

for _nm, _repo in CYBER_TOOLS:
    SOURCES.append({
        "name": _nm,
        "url": "https://github.com/" + _repo + "/releases.atom",
        "country": "WORLD", "lang": "en",
        "topic": "cyber", "cyber_cat": "CYBER_TOOL", "release": True, "boost": 10,
    })

for _nm, _cid, _cat, _bs in CYBER_VIDEOS:
    SOURCES.append({
        "name": _nm,
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=" + _cid,
        "country": "WORLD", "lang": "en",
        "topic": "cyber", "cyber_cat": _cat, "boost": _bs,
    })

for _cat, _nm, _q, _loc, _bs in CYBER_QUERIES:
    SOURCES.append({
        "name": "Cyber " + _nm,
        "url": "https://news.google.com/rss/search?q="
               + urllib.parse.quote(_q + " when:7d") + CYBER_LOC[_loc],
        "country": "ID" if _loc == "id" else "WORLD",
        "lang": _loc,
        "topic": "cyber", "cyber_cat": _cat, "boost": _bs,
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

# --- Kata kunci sepak bola ---
# Dipakai dengan pencocokan batas kata (count_genre_kw), bukan substring
# biasa: "gol" ada di dalam "golongan", "tim" ada di dalam "timetable",
# "liga" ada di dalam "religasi".
BOLA_KW = [
    "sepak bola", "bola", "football", "soccer", "kick-off", "kickoff",
    "klub", "club", "timnas", "pemain", "pelatih", "wasit", "referee",
    "gawang", "keeper", "kiper", "penalti", "kartu kuning", "kartu merah",
    "pertandingan", "match", "skor", "liga", "stadium", "stadion", "suporter",
    "fifa", "uefa", "conmebol", "the afc", "piala", "cup", "champions",
    "manajer", "manager", "coach", "goal", "assist", "persib", "persija",
    "persebaya", "persis", "arema", "bali united", "psm makassar", "persipura",
    "persela", "dewa united", "garuda select", "pssi",
]
BOLA_LIGA_KW = [
    "liga champions", "champions league", "premier league", "la liga",
    "liga bbla", "serie a", "bundesliga", "ligue 1", "eredivisie",
    "liga 1", "liga 2", "liga 3", "piala dunia", "world cup", "piala asia",
    "piala euro", "euro 2024", "aff championship", "club world cup",
    "piala klub dunia", "europa league", "conference league", "super league",
    "isl", "mls", "saudi pro league", "piala antar tim", "liga champion",
    "klasemen", "standings", "quarter-final", "semi final", "finalissima",
]
BOLA_TRANSFER_KW = [
    "transfer", "jual beli", "rekrut", "merekrut", "mendatangkan",
    "melepas", "dilepas", "loan", "pinjaman", "kontrak", "contract",
    "gaji", "wage", "buyout", "klausul", "tawaran", "deal", "bergabung",
    "pindah klub", "ganti klub", "free agent", "free transfer",
    "biaya transfer", "uang transfer", "resmi rekrut", "resmi transferred",
]
BOLA_NASIONAL_KW = [
    "timnas indonesia", "timnas", "pssi", "liga 1", "liga 2", "liga 3",
    "indonesia u-17", "indonesia u-19", "indonesia u-20", "indonesia u-23",
    "garuda select", "piala aff", "aff championship", "piala asia junior",
    "piala dunia 2026 indonesia", "kualifikasi piala dunia",
    "jadwal liga 1", "persib", "persija", "persebaya", "arema", "persis",
    "bali united", "persipura", "persela solo", "dewa united", "psm makassar",
    "bhayangkara", "madura united", "persebaya fifty", "aceh fc", "persikas",
]

# --- keamanan siber ---
# Kata kunci inti. Dipakai sebagai sinyal "ini artikel cyber" untuk sumber
# umum, dan sebagai penjaga anti-noise. Penentuan bidang ada di CYBER_FIELD_KW.
CYBER_KW = [
    "cybersecurity", "cyber security", "cyberattack", "cyber attack",
    "vulnerability", "vulnerabilities", "exploit", "exploited", "exploitation",
    "zero-day", "zero day", "malware", "ransomware", "backdoor", "trojan",
    "botnet", "phishing", "infostealer", "stealer", "rootkit", "spyware",
    "data breach", "data leak", "breach", "exfiltration", "ddos",
    "penetration test", "pentest", "red team", "bug bounty", "cve",
    "rce", "remote code execution", "sql injection", "buffer overflow",
    "use-after-free", "privilege escalation", "supply chain attack",
    "credential", "malicious", "attacker", "intrusion", "compromise",
    "threat actor", "apt", "hacker", "hackers", "cybercrime",
    "keamanan siber", "serangan siber", "kerentanan", "celah keamanan",
    "peretasan", "eksploitasi", "exploit kit", "root access",
]

# Tiap bidang punya daftar kata kunci sendiri. Skor = jumlah kata yang cocok,
# bidang dengan skor tertinggi yang menang. Urutan array jadi prioritas saat
# skor seri: yang lebih spesifik diletakkan lebih dulu (VULN sebelum MALWARE,
# MALWARE sebelum APT, dst.) supaya "ransomware" tidak jatuh ke APT hanya
# karena judulnya juga menyebut "cyberattack".
CYBER_FIELD_KW = [
    ("CYBER_VULN", [
        "cve", "zero-day", "zero day", "0day", "n-day", "actively exploited",
        "exploited in the wild", "known exploited", "kev catalog",
        "security update", "security patch", "security fix", "security advisory",
        "patch tuesday", "vulnerability disclosure", "cvss", "msrc",
        "out-of-band", "critical bug", "hotfix", "patched", "unpatched",
        "vulnerabilities in", "affected versions", "remote code execution",
        "privilege escalation", "buffer overflow", "use-after-free",
        "path traversal", "deserialization", "type confusion",
        "memory corruption", "out-of-bounds", "auth bypass",
        "kerentanan", "celah keamanan", "ditambal", "pembaruan keamanan",
    ]),
    ("CYBER_MALWARE", [
        "ransomware", "malware", "trojan", "botnet", "backdoor", "rootkit",
        "infostealer", "info-stealer", "stealer", "worm", "keylogger",
        "cryptominer", "cryptojacking", "loader", "dropper", "spyware",
        "adware", "remote access trojan", "ransom", "data extortion",
        "extortion", "banking trojan", "malicious software", "wiper",
        "malware sample", "bot herder", "zombie network",
        "perangkat lunak berbahaya", "penyadap",
    ]),
    ("CYBER_BREACH", [
        "data breach", "data leak", "records exposed", "leaked data",
        "database leak", "customer data", "personal data", "stolen data",
        "credential leak", "credentials leaked", "hacked account", "doxx",
        "privacy breach", "exposed database", "misconfigured database",
        "sensitive data", "user data", "millions of records",
        "kebocoran data", "data bocor", "data pribadi",
    ]),
    ("CYBER_APT", [
        "advanced persistent threat", "nation-state", "state-sponsored",
        "state sponsored", "threat actor", "threat group", "cyber espionage",
        "espionage", "cyber campaign", "attribution", "threat intelligence",
        "indicator of compromise", "indicators of compromise", "ioc",
        "targeted attack", "apt", "lazarus", "sandworm", "cozy bear",
        "fancy bear", "midnight blizzard", "volt typhoon", "salt typhoon",
        "qakbot", "cyberattack", "cyber attack", "hacker group",
        "espionase", "kelompok peretas",
    ]),
    ("CYBER_BUG", [
        "bug bounty", "hackerone", "bugcrowd", "yeswehack", "intigriti",
        "patchstack", "responsible disclosure", "disclosure", "bug hunter",
        "proof of concept", "proof-of-concept", "poc", "bounty", "payout",
        "penetration test", "pentest", "adversary simulation",
        "writeup", "write-up", "bug report", "attack chain",
        "security research", "security researcher", "security researchers",
        "kerentanan dilaporkan", "laporan kerentanan",
    ]),
    ("CYBER_TOOL", [
        "security tool", "pentest tool", "hacking tool", "recon tool",
        "reconnaissance", "exploitation framework", "c2 framework",
        "c2 server", "command-and-control", "gadget chain",
        "fuzzer", "fuzzing", "port scanner", "osint",
        "burp suite", "metasploit", "nuclei", "sqlmap", "impacket",
        "bloodhound", "cobalt strike", "mimikatz", "hashcat", "kali linux",
        "parrot os", "offensive security", "ctf", "capture the flag",
        "exploit kit", "post-exploitation", "credential dumping",
        "red team tool",
    ]),
    ("CYBER_BLUE", [
        "blue team", "dfir", "digital forensics", "forensics", "forensic",
        "incident response", "threat hunting", "threat detection", "siem",
        "detection engineering", "edr", "xdr", "telemetry", "hardening",
        "detection rule", "sigma rule", "yara rule", "log analysis",
        "memory forensics", "security operations", "purple team",
        "remediation", "artifact analysis", "triage",
    ]),
    ("CYBER_CLOUD", [
        "cloud security", "amazon web services", "aws", "azure",
        "google cloud", "gcp", "kubernetes", "container security", "docker",
        "serverless", "s3 bucket", "misconfiguration", "cloud misconfiguration",
        "terraform", "devsecops", "iam", "identity and access", "eks", "aks",
        "gke", "cloud attack", "cloud environment",
    ]),
    ("CYBER_APP", [
        "application security", "appsec", "web security", "owasp", "sast",
        "dast", "secure coding", "api security", "authentication",
        "authorization", "session hijacking", "cross-site scripting", "xss",
        "csrf", "ssrf", "injection", "broken access control", "access control",
        "browser vulnerability", "content security policy", "secure sdlc",
        "keamanan aplikasi",
    ]),
    ("CYBER_RE", [
        "reverse engineering", "disassembler", "decompiler", "ghidra",
        "ida pro", "binary ninja", "radare2", "malware analysis", "unpacker",
        "static analysis", "dynamic analysis", "firmware analysis", "shellcode",
        "assembly code", "patch diffing", "binary analysis", "opcode",
        "rekayasa balik", "analisis malware",
    ]),
    ("CYBER_AI", [
        "ai security", "llm security", "prompt injection", "adversarial ml",
        "ai agent", "ai model", "generative ai",
        "jailbreak", "deepfake", "model poisoning", "data poisoning",
        "ai attack", "ai-powered", "ai powered",
        "large language model", "keamanan ai",
    ]),
    ("CYBER_GRC", [
        "regulation", "regulatory", "compliance", "gdpr", "nis2", "dora",
        "privacy law", "data protection", "iso 27001", "pci dss", "audit",
        "governance", "risk management", "legislation", "lawmakers",
        "cybersecurity law", "penalty", "penalties",
        "certification", "regulasi", "kepatuhan", "kebijakan keamanan",
    ]),
]

# Judul rilis tool dari GitHub cuma "v3.11.1", jadi nomor versi ikut dipakai
# sebagai sinyal. Tanpa trailing titik: `kw_word` menolak token berujung
# non-alfanumerik ("v3." tidak akan cocok dengan "v3.11").
CYBER_REL_KW = ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9",
                "rilis", "launches", "adds support"]

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
    # Feed rilis tool (GitHub releases) judulnya cuma nomor versi: "v3.11.1".
    # Tanpa nama tool, tidak ada yang bisa dibaca dari daftar berita.
    if src.get("release") and title and not title.lower().startswith(src_name.lower()):
        title = "%s rilis %s" % (src_name, title)
    # Google News mengisi <description> dengan "judul + nama situs", jadi 83%
    # deskripsi itu mengulang judul. Menampilkannya dua kali cuma menambah
    # bobot payload tanpa menambah informasi. Feed sosial dikecualikan: isi
    # postingannya memang deskripsi, bukan pengulangan judul.
    if desc and not src.get("social"):
        n_t = re.sub(r"[^a-z0-9]+", "", title.lower())
        n_d = re.sub(r"[^a-z0-9]+", "", desc.lower())
        if n_t and n_d.startswith(n_t):
            desc = ""
    return {
        "title": title,
        "url": link,
        "source": src_name,
        "country": src.get("country", ""),
        "lang": src.get("lang", ""),
        "topic": src.get("topic"),
        "genre": src.get("genre"),
        "bola_cat": src.get("bola_cat"),
        "cyber_cat": src.get("cyber_cat"),
        "release": src.get("release"),
        "social": src.get("social"),
        "boost": int(src.get("boost") or 0),
        "published": pub.isoformat() if pub else None,
        "pub_ts": pub.timestamp() if pub else None,
        "desc": desc,
    }


def parse_rss(root, src):
    out = []
    for it in root.findall(".//item"):
        link = (it.findtext("link") or "").strip()
        title = (it.findtext("title") or "").strip()
        if not title:
            # Mastodon dan sebagian feed sosial tidak mengisi <title>;
            # isi postingan ada di <description>. Pakai potongan awalnya.
            raw = re.sub(r"<[^>]+>", " ",
                         htmllib.unescape(it.findtext("description") or ""))
            title = re.sub(r"\s+", " ", raw).strip()[:120]
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
        if not desc:
            # Feed rilis GitHub tidak pakai <summary>, catatan rilisnya ada
            # di <content type="html">.
            desc = it.findtext(ATOM_NS + "content") or ""
        # GitHub hanya mengisi <updated>, tidak ada <published>.
        date = parse_date(it.findtext(ATOM_NS + "published")) or \
            parse_date(it.findtext(ATOM_NS + "updated"))
        out.append(make_item(src, src["name"], title, link,
                             clean_desc(desc), date))
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
    url = src["url"]
    # YouTube membalas 404 kalau terlalu banyak request paralel dari satu IP,
    # dan 404 itu identik dengan "channel memang tidak ada". Satu percobaan
    # ulang setelah jeda sudah cukup untuk membedakan keduanya.
    for attempt in (0, 1):
        try:
            req = urllib.request.Request(url, headers=FEED_HEADERS)
            raw = urllib.request.urlopen(req, timeout=8).read()
            break
        except Exception:
            if attempt or "youtube.com/feeds" not in url:
                raise
            time.sleep(1.5)
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


# Query Google News bola banyak menarik halaman situs betting yang menyamar
# sebagai berita. Pola ini terlalu spesifik buat berita sungguhan, jadi
# dibuang sebelum tampil.
SPAM_RE = re.compile(
    r"\b(toto(on)?|judol|slot ?gacor|slot online|situs (?:bola|slot)|wdytoto|"
    r"situs prediksi|bonus (?:deposit|new member)|ovoDana|totoon|"
    r"syarat betting|correct score betting)\b", re.I)


def is_spam(text):
    return bool(SPAM_RE.search(text))


CYBER_DEFAULT = "CYBER_APT"


def cyber_category(hint, scores):
    """Pilih salah satu dari 12 bidang cyber.

    Sumber yang memang khusus satu bidang punya `cyber_cat`, jadi petunjuk itu
    yang menang. Untuk media umum, bidang dengan skor kata kunci tertinggi yang
    dipakai; urutan CYBER_FIELD_KW jadi penentu saat skor seri."""
    if hint:
        return hint
    best, bs = None, 0
    for code, _ in CYBER_FIELD_KW:
        s = scores.get(code, 0)
        if s > bs:
            best, bs = code, s
    return best or CYBER_DEFAULT


def bola_category(hint, bl, li, tr, na):
    """Pilih tab sepak bola.

    Sumber query Google News bola sudah punya `bola_cat` (sumbernya memang
    dibuat khusus topik itu), jadi petunjuk itu yang menang. Klasifikasi
    kata kunci hanya cadangan untuk media umum seperti CNN/detik yang memuat
    campuran olahraga."""
    if hint == "NASIONAL" and (na > 0 or li > 0 or tr == 0):
        return "BOLA_NASIONAL"
    if hint == "LIGA" and (li > 0 or bl > 0):
        return "BOLA_LIGA"
    if hint == "TRANSFER" and (tr > 0 or bl > 0):
        return "BOLA_TRANSFER"
    if hint == "BOLA" and bl > 0:
        return "BOLA"
    if na > bl:
        return "BOLA_NASIONAL"
    if tr > max(li, 1):
        return "BOLA_TRANSFER"
    if li > 0:
        return "BOLA_LIGA"
    return "BOLA"


def keyword_classify(arts):
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    for a in arts:
        # Buang halaman betting/OLX yang menyamar sebagai berita.
        if is_spam(a["title"] + " " + (a.get("desc") or "")):
            a["drop"] = True
            continue
        # Nama ikut dinilai: "Eurogamer Reviews" memperkuat deteksi review,
        # "Nintendo of America" memicu kata kunci game.
        topic = a.get("topic")
        t = (a["title"] + " " + (a.get("source") or "")).lower()
        # Feed sosial (Mastodon) isinya pendek; isi postingan ada di desc,
        # jadi ikut dinilai supaya kata kunci bidang cyber tidak terlewat.
        if a.get("social") and a.get("desc"):
            t += " " + a["desc"].lower()
        # Nama sumber yang berbentuk domain ("mmorpg.com", "platformer.news")
        # bukan sinyal genre: yang menyebut cuma nama situsnya, bukan isi berita.
        src = a.get("source") or ""
        if "." in src and " " not in src:
            src = ""
        g = count_kw(t, GAME_KW)
        es = count_kw(t, ESPORTS_KW)
        rv = count_kw(t, REVIEW_KW)
        hw = count_kw(t, HARDWARE_KW)
        bl = count_genre_kw(t, BOLA_KW)
        li = count_genre_kw(t, BOLA_LIGA_KW)
        bt = count_genre_kw(t, BOLA_TRANSFER_KW)
        na = count_genre_kw(t, BOLA_NASIONAL_KW)
        cy = count_genre_kw(t, CYBER_KW)
        cy_scores = {code: count_genre_kw(t, kws) for code, kws in CYBER_FIELD_KW}
        rl = count_genre_kw(t, CYBER_REL_KW)
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
        elif topic == "bola":
            # Sumber bola tidak boleh masuk GENTING: kata "serangan" dan "bom"
            # di judul berita bola akan salah jadi berita perang.
            # Wajib ada sinyal sepak bola: query Google News yang luas
            # ("PSSI") sesekali menarik halaman yang sama sekali bukan bola.
            if bl + li + bt + na == 0:
                a["drop"] = True
                continue
            cat = bola_category(a.get("bola_cat"), bl, li, bt, na)
            base = 44 + bl * 5 + max(li, bt, na) * 8
        elif topic == "cyber":
            # Sumber cyber tidak boleh masuk GENTING: kata "attack"/"exploit"
            # di judul kerentanan akan salah jadi berita perang. Ini urutan
            # penting, cyber harus dicek sebelum GENTING.
            is_release = a.get("release")
            strongest = max(cy_scores.values()) if cy_scores else 0
            if cy + sum(cy_scores.values()) + rl == 0 and not is_release:
                a["drop"] = True
                continue
            # Post sosial sering cuma menyinggung kata umum ("Hacker News",
            # nama podcast). Wajib ada sinyal bidang yang jelas.
            if a.get("social") and not is_release and strongest == 0:
                a["drop"] = True
                continue
            if is_release:
                # Feed rilis first-party: judulnya nomor versi, kategorinya
                # sudah pasti tool. Tidak perlu ditebak kata kunci.
                cat = "CYBER_TOOL"
            else:
                cat = cyber_category(a.get("cyber_cat"), cy_scores)
            base = 45 + cy * 5 + strongest * 9 + (6 if is_release else 0)
        elif gg > 0:
            cat = "GENTING"
            base = 55 + gg * 12
        elif tr > 0:
            cat = "TRADER"
            base = 45 + tr * 9
        elif bl >= 2 and bl * 2 >= (pi + pe + g):
            # Media umum (CNN Indonesia, detik, Antara) memuat campuran berita
            # politik dan olahraga. Butuh minimal 2 kata kunci sepak bola
            # supaya judul politik tidak ikut terambil.
            cat = bola_category(None, bl, li, bt, na)
            base = 40 + bl * 6
        elif cy >= 2 and cy * 2 >= (pi + pe + g + bl):
            # Media umum (BBC, Reuters, CNBC) sesekali membawa berita cyber.
            # Butuh minimal 2 kata kunci supaya judul politik biasa tidak
            # ikut terambil - kata "breach" dan "exploit" mudah muncul
            # dalam konteks lain.
            cat = cyber_category(None, cy_scores)
            base = 41 + cy * 6
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

        # Genre hanya relevan buat tab game. Tanpa penjaga ini berita bola
        # yang kebetulan kena filter kata kunci game ("FIFA 26", "RPG")
        # akan muncul dengan chip genre yang menyesatkan.
        if cat not in GAME_CATS:
            a["genres"] = []
            a["genre_main"] = None
            continue
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
                    # Post sosial sering mengutip judul artikel yang sama dengan
                    # media. Kalau digabung, sumber sosialnya hilang dari daftar,
                    # jadi kunci sosial disendirikan per akun.
                    if it.get("social"):
                        key += "|" + it["source"]
                    if not key or key == "|":
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
    head = arts[:MAX_ARTICLES * 10]
    # Feed rilis tool sering kalah umur dari ribuan artikel Google News 7 hari
    # terakhir, sehingga rilis yang masih baru ikut terpotong. Rilis dalam
    # 90 hari terakhir selalu diikutkan, yang lebih tua dibiarkan tersapu.
    fresh_rel = [a for a in arts
                 if a.get("release") and a.get("pub_ts")
                 and time.time() - a["pub_ts"] <= 90 * 86400]
    # Proyek yang rilis harian (nuclei-templates dsb.) tidak boleh membanjiri
    # tab tool: ambil maksimal 3 rilis terbaru per proyek.
    per_src, picked = {}, []
    for a in fresh_rel:  # arts sudah urut terbaru dulu
        lst = per_src.setdefault(a["source"], [])
        if len(lst) < 3:
            lst.append(a)
            picked.append(a)
    fresh_rel = picked
    if len(fresh_rel) <= 250:
        kept_ids = {id(a) for a in head}
        head = head + [a for a in fresh_rel if id(a) not in kept_ids]
    arts = head
    for a in arts:
        a["source_main"] = a["sources"][0] if a["sources"] else a["source"]
        a["source_count"] = len(a["sources"])
    return arts, ok, fail


def balance_categories(arts):
    """Pangkas artikel dengan giliran (round-robin) supaya sumber paling rame
    tidak menyingkirkan kelompok topik lain.

    Tiga tahap, masing-masing dengan jatah dari FAMILY_SHARE:
      1. "other"  - Genting/Politik/Trader/Lainnya, giliran antar kategori.
      2. "game"   - giliran per genre utama (bukan per kategori), supaya
                    genre minim berita seperti Strategy tetap punya isinya.
      3. "bola"   - giliran per kategori, supaya bola tidak menimpa news
                    game dan sebaliknya.

    Semua tahap tetap memakai plafon MAX_PER_CAT per kategori. Artikel
    terpanas di tiap kelompok selalu ikut, urutan akhir berdasarkan hotness.
    """
    groups = {fam: {} for fam in FAMILY_SHARE}
    for a in arts:
        cat = a["category"]
        fam = family_of(cat)
        if fam == "game":
            key = a.get("genre_main") or "-"
        else:
            key = cat
        groups[fam].setdefault(key, []).append(a)
    for fam in groups:
        for items in groups[fam].values():
            items.sort(key=lambda a: -a["hotness"])

    kept = []
    cat_count = {}
    for fam in ("other", "game", "bola", "cyber"):
        fam_groups = groups[fam]
        budget = int(MAX_ARTICLES * FAMILY_SHARE[fam])
        # Jatah keluarga ini adalah tambahan, bukan ambang total. Kalau dipakai
        # sebagai `len(kept) < budget`, keluarga pertama saja yang terisi.
        start = len(kept)
        i = 0
        while len(kept) - start < budget:
            added = False
            for key in sorted(fam_groups):
                if i >= len(fam_groups[key]):
                    continue
                a = fam_groups[key][i]
                cat = a["category"]
                if cat_count.get(cat, 0) >= MAX_PER_CAT:
                    continue
                if len(kept) - start >= budget:
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
