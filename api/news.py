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
import urllib.request
import xml.etree.ElementTree as ET

CATS = [
    ("GENTING", "Genting / Urgent", "#ff4d4d"),
    ("POLITIK_ID", "Politik Dalam Negeri", "#4da6ff"),
    ("POLITIK_INT", "Politik Internasional", "#8a6dff"),
    ("TRADER", "Trader / Pasar", "#ffc14d"),
    ("LAINNYA", "Lainnya", "#7a8290"),
]

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
]

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
    "diplomacy", "sanctions", "trade war", "geopolitik", "summit", "g7", "g20",
    "brics", "asean", "treaty", "ambassador", "regime", "election results",
    "bilateral", "minister says", "foreign ministry",
]
ID_HINT_WORDS = [
    "yang", "dengan", "untuk", "dalam", "akan", "presiden", "indonesia",
    "jakarta", "pemerintah", "sehingga", "karena", "oleh", "para",
]


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


def fetch_feed(src):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    req = urllib.request.Request(src["url"], headers=headers)
    raw = urllib.request.urlopen(req, timeout=8).read()
    root = ET.fromstring(raw)
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
        pub = parse_rfc822(it.findtext("pubDate"))
        desc = it.findtext("description") or ""
        desc = re.sub(r"<[^>]+>", " ", desc)
        desc = htmllib.unescape(desc).strip()
        if len(desc) < 45 or desc.lower().startswith(("read more", "http", "untuk selengkapnya")):
            desc = ""
        out.append(
            {
                "title": title,
                "url": link,
                "source": src_name,
                "country": src.get("country", ""),
                "lang": src.get("lang", ""),
                "published": pub.isoformat() if pub else None,
                "pub_ts": pub.timestamp() if pub else None,
                "desc": desc[:280],
            }
        )
    return out


def detect_lang(text):
    t = text.lower()
    hits = sum(1 for w in ID_HINT_WORDS if w in t.split())
    return "id" if hits >= 1 else "en"


def keyword_classify(arts):
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    for a in arts:
        t = a["title"].lower()
        g = sum(1 for k in GENTING_KW if k in t)
        tr = sum(1 for k in TRADER_KW if k in t)
        pi = sum(1 for k in POL_ID_KW if k in t)
        pe = sum(1 for k in POL_INT_KW if k in t)
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
        if g > 0:
            cat = "GENTING"
            base = 55 + g * 12
        elif tr > 0:
            cat = "TRADER"
            base = 45 + tr * 9
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
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
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
                        continue
                    it["id"] = title_id(it["title"])
                    it["sources"] = [it["source"]]
                    raw[key] = it
            except Exception as e:
                fail.append(s["name"] + " (" + str(e)[:40] + ")")
    arts = list(raw.values())
    arts.sort(key=lambda a: a.get("pub_ts") or 0, reverse=True)
    arts = arts[:160]
    for a in arts:
        a["source_main"] = a["sources"][0] if a["sources"] else a["source"]
        a["source_count"] = len(a["sources"])
    return arts, ok, fail


def build_state():
    arts, ok, fail = collect_all()
    keyword_classify(arts)
    merge_cluster_boost(arts)
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
                "articles": [],
            })

    if path == "/api/health":
        return respond(start_response, 200, {"ok": True, "service": "news-api"})

    start_response("404 Not Found", [("Content-Type", "application/json")])
    return [b'{"error":"not found"}']
