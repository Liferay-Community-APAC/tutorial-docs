#!/usr/bin/env python3
"""Generate synthetic webserver logs in the traffic-measurement format, for demos.

Writes one gzipped log file per UTC day. The traffic is invented: residential
visitors with the beacon, signed-in users, visitors without JavaScript, real
search engine crawler addresses, scrapers on cloud addresses (with a scraping
campaign in the middle of the period), HTTP scripts, declared SEO bots and an
uptime monitor.

Usage: make_sample_logs.py OUT_DIR AWS_JSON [--days 30] [--end 2026-11-24]
"""

import argparse
import datetime as dt
import gzip
import json
import os
import random
from urllib.parse import quote

HOST = "www.example.co.jp"
PAGES = (["/", "/ja/products", "/ja/products/cloud-platform", "/ja/products/analytics", "/ja/solutions",
          "/ja/news", "/ja/contact", "/ja/careers", "/en", "/en/products", "/en/news",
          "/ja/" + quote("お知らせ"), "/ja/" + quote("製品情報") + "/2026", "/ja/" + quote("会社概要")]
         + ["/ja/news/2026/%02d/%s" % (m, s) for m in range(6, 12) for s in ("release", "event", "update")]
         + ["/ja/products/item-%d" % i for i in range(1, 41)])
HEAVY = ["/ja/search?q=%s" % quote(w) for w in ("料金", "導入事例", "API", "セキュリティ", "pricing")]
CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36"
MAC_SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.1 Safari/605.1.15"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 19_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.1 Mobile/15E148 Safari/604.1"
FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
BINGBOT = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
DECLARED = ["Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)",
            "Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)",
            "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"]
MONITOR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 DynatraceSynthetic/1.0 monitor"
SCRIPTS = ["python-requests/2.32.3", "curl/8.11.1", "Go-http-client/2.0", "Java/21.0.5", "axios/1.8.4"]
HEADLESS = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/150.0.0.0 Safari/537.36"


def esc(v):
    return str(v).replace('"', "\\x22")


class Day:
    def __init__(self, day, rng):
        self.day = day
        self.rng = rng
        self.lines = []

    def log(self, t, ip, ua, uri, method="GET", status="200", ct="text/html;charset=UTF-8", b=None,
            urt=None, full=True, cookie_support=True, auth=False, al="ja,en-US;q=0.9,en;q=0.8"):
        rng = self.rng
        if not 0 <= t < 86400:
            return          # keep every line inside its own UTC day
        ts = (dt.datetime.combine(self.day, dt.time(), dt.timezone.utc) + dt.timedelta(seconds=t)).isoformat()
        is_page = ct.startswith("text/html")
        if b is None:
            b = rng.randint(28000, 140000) if is_page else rng.randint(2000, 60000)
        if urt is None:
            urt = round(rng.uniform(0.04, 0.6), 3) if is_page else round(rng.uniform(0.002, 0.03), 3)
        hdr = {
            "al": al if full else "-",
            "acc": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" if full else "*/*",
            "sfs": "same-origin" if full else "-", "sfm": "navigate" if full else "-", "sfd": "document" if full else "-",
            "chua": '"Chromium";v="150", "Google Chrome";v="150"' if full and "Chrome" in ua else "-",
            "chp": '"Windows"' if full and "Chrome" in ua else "-",
        }
        self.lines.append((t, (
            f'tm=1 ts="{ts}" xff="{ip}, 10.12.0.4" ra="{ip}" host="{HOST}" m="{method}" uri="{esc(uri)}" '
            f's="{status}" ct="{ct if ct else "-"}" b="{b if method == "GET" else 0}" rt="{urt}" '
            f'urt="{urt if not uri.startswith("/_tm/") else "-"}" ua="{esc(ua)}" ref="-" al="{hdr["al"]}" '
            f'acc="{hdr["acc"]}" sfs="{hdr["sfs"]}" sfm="{hdr["sfm"]}" sfd="{hdr["sfd"]}" chua="{esc(hdr["chua"])}" '
            f'chp="{esc(hdr["chp"])}" cs="{"true" if cookie_support else "-"}" auth="{"1" if auth else ""}" '
            f'rid="{rng.getrandbits(64):016x}"')))

    def page_with_assets(self, t, ip, ua, path, beacon=True, interact=True, **kw):
        rng = self.rng
        self.log(t, ip, ua, path, **kw)
        for _ in range(rng.randint(3, 7)):
            self.log(t + rng.uniform(0.1, 2), ip, ua, "/o/theme/%s.%s?v=8" % (rng.choice("abcdef"), rng.choice(["css", "js", "png", "woff2"])),
                     ct=rng.choice(["text/css", "application/javascript", "image/png", "font/woff2"]), **kw)
        if beacon:
            p = quote(path.split("?")[0], safe="")
            self.log(t + rng.uniform(0.5, 3), ip, ua, f"/_tm/b?t=load&p={p}&n=x", method="POST", status="204", ct="", **kw)
            if interact:
                self.log(t + rng.uniform(2, 20), ip, ua, f"/_tm/b?t=int&p={p}&n=x", method="POST", status="204", ct="", **kw)


def residential_ip(rng):
    # Japanese consumer and mobile ranges (illustrative)
    first = rng.choice([1, 14, 27, 36, 42, 49, 60, 61, 101, 106, 110, 114, 118, 121, 124, 126, 133, 153, 180, 182, 202, 210, 219, 220])
    return f"{first}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def cloud_ips(aws_json, rng, n):
    prefixes = [p["ip_prefix"] for p in json.load(open(aws_json))["prefixes"] if p["ip_prefix"].endswith(("/16", "/15", "/14"))]
    out = []
    for _ in range(n):
        net = rng.choice(prefixes).split("/")[0].split(".")
        out.append(f"{net[0]}.{net[1]}.{rng.randint(0, 255)}.{rng.randint(1, 254)}")
    return out


def daytime(rng):
    """Seconds since midnight UTC, weighted to Japanese daytime (UTC+9)."""
    jst_hour = rng.choices(range(24), weights=[2, 1, 1, 1, 1, 2, 4, 7, 10, 12, 12, 11, 10, 11, 12, 12, 11, 10, 9, 9, 8, 6, 4, 3])[0]
    return ((jst_hour - 9) % 24) * 3600 + rng.uniform(0, 3599)


def build_day(day, idx, n_days, rng, scraper_pool):
    d = Day(day, rng)
    weekend = day.weekday() >= 5
    growth = 1 + 0.004 * idx
    visitors = int(rng.gauss(620 if weekend else 1450, 60) * growth)

    for _ in range(visitors):
        ip = residential_ip(rng)
        ua = rng.choices([CHROME.format(v=rng.choice([148, 149, 150])), MAC_SAFARI, IPHONE, FIREFOX], [55, 15, 22, 8])[0]
        signed_in = rng.random() < 0.08
        no_js = rng.random() < 0.02
        t = daytime(rng)
        for k in range(rng.choices([1, 2, 3, 4, 6], [40, 25, 15, 12, 8])[0]):
            path = rng.choice(PAGES) if rng.random() > 0.05 else rng.choice(HEAVY)
            d.page_with_assets(t, ip, ua, path, beacon=not no_js, interact=rng.random() < 0.85,
                               cookie_support=k > 0 or rng.random() < 0.3, auth=signed_in)
            t += rng.uniform(15, 240)
        if rng.random() < 0.03:
            d.log(t, ip, ua, "/ja/old-page", status="404")

    # Verified search engines (real crawler addresses with matching DNS)
    for _ in range(rng.randint(260, 340)):
        ip = f"66.249.66.{rng.randint(1, 40)}"
        d.log(daytime(rng), ip, GOOGLEBOT, rng.choice(PAGES), full=False, cookie_support=False, al="-")
    for _ in range(rng.randint(90, 140)):
        ip = f"157.55.39.{rng.randint(1, 60)}"
        d.log(daytime(rng), ip, BINGBOT, rng.choice(PAGES), full=False, cookie_support=False, al="-")

    # Declared SEO / AI crawlers
    for ua in DECLARED:
        ip = rng.choice(scraper_pool)
        for _ in range(rng.randint(80, 260)):
            d.log(daytime(rng), ip, ua, rng.choice(PAGES), full=False, cookie_support=False, al="-")

    # Uptime monitor every 5 minutes
    for k in range(288):
        d.log(k * 300 + rng.uniform(0, 5), "52.95.110.1", MONITOR, "/", full=False, cookie_support=False, al="-")

    # Fake Googlebots on cloud addresses
    for _ in range(rng.randint(30, 80)):
        d.log(daytime(rng), rng.choice(scraper_pool), GOOGLEBOT, rng.choice(PAGES + HEAVY), full=False, cookie_support=False, al="-")

    # HTTP scripts
    for _ in range(rng.randint(150, 400)):
        d.log(daytime(rng), rng.choice(scraper_pool[:20]), rng.choice(SCRIPTS), rng.choice(PAGES), full=False,
              cookie_support=False, al="-")

    # Headless browsers
    for _ in range(rng.randint(40, 120)):
        d.log(daytime(rng), rng.choice(scraper_pool), HEADLESS, rng.choice(PAGES), full=False, cookie_support=False)

    # Browser-like scrapers on cloud addresses: no beacon, missing browser headers, bursts
    campaign = n_days // 2 - 3 <= idx <= n_days // 2 + 1
    bursts = rng.randint(6, 12) + (55 if campaign else 0)
    for _ in range(bursts):
        ip = rng.choice(scraper_pool)
        ua = CHROME.format(v=rng.choice([120, 131, 150]))
        t = daytime(rng)
        for _ in range(rng.randint(60, 220)):
            path = rng.choice(PAGES + HEAVY * 3)
            d.log(t, ip, ua, path, full=False, cookie_support=False, al="-",
                  urt=round(rng.uniform(0.8, 2.5), 3) if "search" in path else None)
            t += rng.uniform(0.8, 1.6)
        if rng.random() < 0.3:
            d.log(t, ip, ua, "/_tm/hp/", status="204", ct="", full=False, cookie_support=False, al="-")

    # Residential-proxy scrapers that look almost human (land in "uncertain")
    for _ in range(rng.randint(150, 300)):
        ip = residential_ip(rng)
        ua = CHROME.format(v=150)
        d.log(daytime(rng), ip, ua, rng.choice(PAGES), al="-", cookie_support=False)

    # Spam queries
    for _ in range(rng.randint(10, 40)):
        d.log(daytime(rng), residential_ip(rng), CHROME.format(v=150), "/ja/search?q=" + quote("https://casino-win.top"), full=False)

    d.lines.sort(key=lambda x: x[0])
    return [line for _, line in d.lines]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("aws_json")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--end", default="2026-11-24")
    args = ap.parse_args()
    rng = random.Random(20261124)
    scraper_pool = cloud_ips(args.aws_json, rng, 300)
    end = dt.date.fromisoformat(args.end)
    os.makedirs(args.out, exist_ok=True)
    total = 0
    for i in range(args.days):
        day = end - dt.timedelta(days=args.days - 1 - i)
        lines = build_day(day, i, args.days, rng, scraper_pool)
        with gzip.open(os.path.join(args.out, f"webserver-example-prd-{day}.log.gz"), "wt") as fh:
            fh.write("\n".join(lines) + "\n")
        total += len(lines)
    print(f"wrote {args.days} days, {total} lines")


if __name__ == "__main__":
    main()
