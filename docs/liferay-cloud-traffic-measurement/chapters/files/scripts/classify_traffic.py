#!/usr/bin/env python3
"""Classify Liferay PaaS webserver page views into human and automated traffic.

Reads access-log lines written with the measurement log format (lines containing
tm=1) and writes daily CSV summaries. Input files may be plain text or .gz, and
may be the files written by the webserver log backup (lines prefixed by lcp).

Usage:
  TM_SALT=... python3 classify_traffic.py --out out logs/*.log.gz
  TM_SALT=... python3 classify_traffic.py --out out --data data --beacon --verify-dns logs/*.gz

Pass all files for the days you want to classify in one run (for example the 24
hourly backup files of one day). Signals such as the honeypot and "no
interaction all day" are computed per UTC day, so a day split across separate
runs is classified less accurately.

Optional: pip install geoip2   (only needed for network and country lookups)
"""

import argparse
import bisect
import collections
import csv
import datetime as dt
import functools
import glob
import gzip
import hashlib
import ipaddress
import json
import os
import re
import socket
import statistics
import sys
from urllib.parse import parse_qs, unquote, urlsplit

RULES_VERSION = "2.0.0"

FIELD_RE = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')
XESC_RE = re.compile(r"\\x([0-9A-Fa-f]{2})")  # Nginx writes " as \x22

# Only these responses are page views: redirects, errors and other statuses are not.
PAGE_STATUSES = {"200", "304"}
EXCLUDED_PATH_PARTS = (
    "extend_session", "expire_session", "update_language", "c/portal/layout",
    "well-known/traffic-advice", "debug/pprof",
)
ASSET_RE = re.compile(r"\.(css|js|mjs|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|map)(\?|$)", re.I)

SEARCH_ENGINE_RE = re.compile(r"googlebot|google-inspectiontool|bingbot|applebot|duckduckbot|yandexbot|baiduspider", re.I)
SEARCH_ENGINE_DNS = (".googlebot.com", ".google.com", ".search.msn.com", ".applebot.apple.com",
                     ".yandex.ru", ".yandex.net", ".yandex.com", ".baidu.com", ".baidu.jp")
DECLARED_BOT_RE = re.compile(r"bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|scan", re.I)
SCRIPT_RE = re.compile(r"curl|wget|python-|python/|go-http-client|java/|okhttp|libwww|scrapy|httpclient|axios|node-fetch|undici|postman|insomnia", re.I)
HEADLESS_RE = re.compile(r"headlesschrome|phantomjs|puppeteer|playwright|selenium|electron", re.I)
CHROMIUM_RE = re.compile(r"(?:Chrome|CriOS|Edg)/(\d+)")
FIREFOX_RE = re.compile(r"Firefox/(\d+)")
SPAM_QUERY_RE = re.compile(r"https?://|www\.|\.(com|net|org|io|xyz|shop|top)\b|discord|telegram|whatsapp|casino|crypto|viagra", re.I)
# Hosting providers matched by network owner. AWS, Google Cloud, Azure and Oracle are
# matched by their published ranges instead, which avoids flagging their consumer or
# office networks.
HOSTING_ORG_RE = re.compile(
    r"digitalocean|ovh|hetzner|linode|akamai|alibaba|tencent|"
    r"contabo|vultr|choopa|leaseweb|scaleway|hostinger|m247|datacamp|cdn77|psychz|colocrossing", re.I)

WEIGHTS = {
    "fake_search_engine": 80,
    "honeypot": 100,
    "webdriver": 60,
    "no_beacon": 35,
    "no_interaction_all_day": 10,
    "no_sec_fetch": 25,
    "no_client_hints": 10,
    "no_accept_language": 15,
    "generic_accept": 10,
    "no_cookie_on_repeat": 10,
    "datacenter_ip": 25,
    "tor_exit": 20,
    "high_rate": 25,
    "few_assets": 20,
    "regular_timing": 15,
    "spam_query": 40,
    "outdated_browser": 15,
    "reads_robots_as_browser": 30,
}
AUTOMATED_AT = 60
UNCERTAIN_AT = 30

# Classes, in report order:
#   human, signed_in, uncertain, automated, script_or_headless, declared_bot,
#   verified_search_engine
# "signed_in" is a page view that passed the bot checks and carried a Liferay
# session-state cookie. The cookie is set by the browser, so it is never used to
# skip the bot checks: an automated client that sends it is still "automated".


def open_log(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", errors="replace")
    return open(path, errors="replace")


def norm_path(p):
    """Decode a path once and drop a trailing slash, so log and beacon paths compare equal."""
    p = unquote(p)
    return p.rstrip("/") or "/"


def parse_line(line):
    if "tm=1" not in line:
        return None
    f = {k: XESC_RE.sub(lambda m: chr(int(m.group(1), 16)), v) for k, v in FIELD_RE.findall(line)}
    if "ts" not in f or "uri" not in f:
        return None
    try:
        f["time"] = dt.datetime.fromisoformat(f["ts"])
    except ValueError:
        return None
    # $remote_addr: Liferay Cloud's nginx already resolves it to the real client
    # (set_real_ip_from the load balancer, real_ip_recursive on). The left end of
    # X-Forwarded-For is written by the client and must not be trusted.
    f["ip"] = sys.intern(f.get("ra", ""))
    parts = urlsplit(f["uri"])
    f["path"] = parts.path
    f["query"] = parts.query
    f["ua"] = sys.intern("" if f.get("ua") == "-" else f.get("ua", ""))
    for k in ("al", "acc", "sfm", "chua", "cs", "auth", "ct", "ref"):
        if f.get(k) == "-":
            f[k] = ""
    f["day"] = f["time"].astimezone(dt.timezone.utc).date().isoformat()
    f["epoch"] = int(f["time"].timestamp())
    return f


def is_page_view(r):
    if r.get("m") != "GET" or r.get("s") not in PAGE_STATUSES:
        return False
    ct = r.get("ct", "").lower()
    if ct and not ct.startswith("text/html"):
        return False
    if not ct and r.get("s") != "304":   # 304 responses carry no content type
        return False
    p = r["path"]
    if p.startswith("/_tm/") or p.startswith("/group/control_panel") or p == "/robots.txt":
        return False
    return not any(part in r["uri"] for part in EXCLUDED_PATH_PARTS)


def is_asset(r):
    return r.get("m") == "GET" and (ASSET_RE.search(r["path"]) is not None or
                                    r.get("ct", "").startswith(("text/css", "application/javascript", "text/javascript", "image/", "font/")))


class RangeIndex:
    """Sorted, merged address ranges per IP version, searched with bisect."""

    def __init__(self, networks):
        self.starts, self.ends, self.labels = {}, {}, {}
        for version in (4, 6):
            spans = sorted((int(n.network_address), int(n.broadcast_address), label)
                           for n, label in networks if n.version == version)
            starts, ends, labels = [], [], []
            for s, e, label in spans:
                if starts and s <= ends[-1] + 1:
                    ends[-1] = max(ends[-1], e)
                else:
                    starts.append(s)
                    ends.append(e)
                    labels.append(label)
            self.starts[version], self.ends[version], self.labels[version] = starts, ends, labels

    def find(self, addr):
        v = addr.version
        i = bisect.bisect_right(self.starts[v], int(addr)) - 1
        if i >= 0 and int(addr) <= self.ends[v][i]:
            return self.labels[v][i]
        return ""


class Enrichment:
    def __init__(self, data_dir):
        networks = []
        self.tor = set()
        self.asn_reader = None
        self.country_reader = None
        if data_dir:
            for name, loader in (("aws.json", self._aws), ("gcp.json", self._google), ("oracle.json", self._oracle),
                                 ("azure.json", self._azure)):
                path = os.path.join(data_dir, name)
                if os.path.exists(path):
                    with open(path) as fh:
                        for cidr, label in loader(json.load(fh)):
                            try:
                                networks.append((ipaddress.ip_network(cidr, strict=False), label))
                            except (TypeError, ValueError):
                                pass
            tor_path = os.path.join(data_dir, "tor-exits.txt")
            if os.path.exists(tor_path):
                with open(tor_path) as fh:
                    self.tor = {line.strip() for line in fh if line.strip() and not line.startswith("#")}
            try:
                import geoip2.database
                asn_db = os.path.join(data_dir, "GeoLite2-ASN.mmdb")
                country_db = os.path.join(data_dir, "GeoLite2-Country.mmdb")
                if os.path.exists(asn_db):
                    self.asn_reader = geoip2.database.Reader(asn_db)
                if os.path.exists(country_db):
                    self.country_reader = geoip2.database.Reader(country_db)
            except ImportError:
                pass
        self.ranges = RangeIndex(networks)
        self.lookup = functools.lru_cache(maxsize=500_000)(self._lookup)

    @staticmethod
    def _aws(d):
        return [(p["ip_prefix"], "AWS") for p in d.get("prefixes", [])] + \
               [(p["ipv6_prefix"], "AWS") for p in d.get("ipv6_prefixes", [])]

    @staticmethod
    def _google(d):
        return [(p.get("ipv4Prefix") or p.get("ipv6Prefix"), "Google Cloud") for p in d.get("prefixes", [])]

    @staticmethod
    def _oracle(d):
        return [(c["cidr"], "Oracle Cloud") for r in d.get("regions", []) for c in r.get("cidrs", [])]

    @staticmethod
    def _azure(d):
        return [(p, "Azure") for v in d.get("values", []) for p in v.get("properties", {}).get("addressPrefixes", [])]

    def _lookup(self, ip):
        info = {"asn": "", "org": "", "country": "", "cloud": "", "tor": ip in self.tor}
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return info
        info["cloud"] = self.ranges.find(addr)
        if self.asn_reader:
            try:
                a = self.asn_reader.asn(ip)
                info["asn"] = str(a.autonomous_system_number or "")
                info["org"] = a.autonomous_system_organization or ""
            except Exception:
                pass
        if self.country_reader:
            try:
                info["country"] = self.country_reader.country(ip).country.iso_code or ""
            except Exception:
                pass
        return info


def reverse_dns_works():
    """Google's public resolver always has a PTR record; if it cannot be read, DNS is unusable."""
    try:
        return socket.gethostbyaddr("8.8.8.8")[0].endswith("dns.google")
    except OSError:
        return False


@functools.lru_cache(maxsize=100_000)
def verified_search_engine(ip):
    """Reverse DNS, then forward DNS must return the same IP."""
    try:
        host = socket.gethostbyaddr(ip)[0].lower()
        if host.endswith(SEARCH_ENGINE_DNS):
            return ip in {ai[4][0] for ai in socket.getaddrinfo(host, None)}
        return False
    except (socket.herror, socket.gaierror):
        return False    # genuine search engine crawlers always have matching PTR records
    except OSError:
        return None     # timeout or DNS outage: cannot tell


def ua_kind(ua):
    if not ua:
        return "script"
    if SEARCH_ENGINE_RE.search(ua):
        return "search_engine_claim"
    if HEADLESS_RE.search(ua):
        return "headless"
    if SCRIPT_RE.search(ua):
        return "script"
    if DECLARED_BOT_RE.search(ua):
        return "declared_bot"
    return "browser"


def ip_hash(ip, salt):
    return hashlib.sha256((salt + ip).encode()).hexdigest()[:16]


def iter_records(files):
    for path in files:
        with open_log(path) as fh:
            for line in fh:
                r = parse_line(line)
                if r:
                    yield r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="log files, plain or .gz (globs allowed)")
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--data", help="enrichment folder written by fetch-enrichment.sh")
    ap.add_argument("--beacon", action="store_true", help="the page beacon is deployed")
    ap.add_argument("--verify-dns", action="store_true", help="verify search engine claims with DNS (slower)")
    ap.add_argument("--detail", action="store_true",
                    help="also write page_views.csv, one row per page view (large; contains personal data)")
    ap.add_argument("--min-chrome", type=int, default=110, help="Chromium versions below this are treated as outdated")
    ap.add_argument("--min-firefox", type=int, default=110)
    ap.add_argument("--rate-limit", type=int, default=30, help="page views per minute from one client treated as high")
    args = ap.parse_args()

    salt = os.environ.get("TM_SALT", "")
    if len(salt) < 16:
        sys.exit("error: set TM_SALT to a random secret of at least 16 characters (IP hashes are reversible without it)")

    verify_dns = args.verify_dns
    if verify_dns:
        socket.setdefaulttimeout(3)
        if not reverse_dns_works():
            print("warning: reverse DNS is not working here; search engine claims will be counted as "
                  "declared bots without verification", file=sys.stderr)
            verify_dns = False

    enrich = Enrichment(args.data)
    files = [f for pattern in args.logs for f in sorted(glob.glob(pattern))]
    if not files:
        sys.exit("error: no input files matched")

    # ---- Pass 1: per-client facts, kept compact ---------------------------------
    load_beacons = collections.defaultdict(list)          # (day, ip, ua, path) -> [epoch]
    client_beacon_types = collections.defaultdict(set)    # (day, ip, ua) -> {types}
    honeypot = set()                                      # (day, ip, ua)
    robots = set()                                        # (day, ip, ua)
    assets = collections.Counter()                        # (day, ip, ua)
    view_times = collections.defaultdict(list)            # (day, ip, ua) -> [epoch]

    for r in iter_records(files):
        key = (r["day"], r["ip"], r["ua"])
        if r["path"] == "/_tm/b":
            q = parse_qs(r["query"])
            t = (q.get("t") or [""])[0]
            client_beacon_types[key].add(t)
            if t == "load":
                p = norm_path((q.get("p") or [""])[0].split("?")[0])
                load_beacons[key + (sys.intern(p),)].append(r["epoch"])
        elif r["path"].startswith("/_tm/hp"):
            honeypot.add(key)
        elif r["path"] == "/robots.txt":
            robots.add(key)
        elif is_page_view(r):
            view_times[key].append(r["epoch"])
        elif is_asset(r):
            assets[key] += 1

    client_flags = {}
    for key, times in view_times.items():
        times.sort()
        peak, j = 0, 0
        for i, t in enumerate(times):
            while t - times[j] > 60:
                j += 1
            peak = max(peak, i - j + 1)
        gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
        regular = len(gaps) >= 5 and statistics.mean(gaps) > 0 and statistics.pstdev(gaps) / statistics.mean(gaps) < 0.15
        client_flags[key] = {
            "high_rate": peak > args.rate_limit,
            "few_assets": len(times) >= 3 and assets[key] / len(times) < 0.2,
            "regular_timing": regular,
            "first": times[0],
            "views": len(times),
        }
    del view_times, assets

    # ---- Pass 2: classify each page view ------------------------------------------
    os.makedirs(args.out, exist_ok=True)
    summary = collections.defaultdict(lambda: [0, 0.0, 0])   # (day, host, cls) -> [views, server_s, bytes]
    day_totals = collections.Counter()
    signal_counts = collections.Counter()
    top_clients = collections.Counter()
    top_paths = collections.Counter()
    page_count = 0

    detail_fh = open(os.path.join(args.out, "page_views.csv"), "w", newline="") if args.detail else None
    detail = csv.writer(detail_fh) if detail_fh else None
    if detail:
        detail.writerow(["day", "time", "host", "path", "status", "class", "score", "signals",
                         "ip_hash", "asn", "org", "country", "cloud", "user_agent", "rules_version"])

    for r in iter_records(files):
        if not is_page_view(r):
            continue
        page_count += 1
        key = (r["day"], r["ip"], r["ua"])
        info = enrich.lookup(r["ip"])
        kind = ua_kind(r["ua"])
        sig = []
        cls = None

        if kind == "search_engine_claim":
            verdict = verified_search_engine(r["ip"]) if verify_dns else None
            if verdict is False:
                sig.append("fake_search_engine")
            else:
                cls = "verified_search_engine" if verdict else "declared_bot"
        elif kind == "declared_bot":
            cls = "declared_bot"
        elif kind in ("script", "headless"):
            cls = "script_or_headless"

        if cls is None:
            flags = client_flags[key]
            if key in honeypot:
                sig.append("honeypot")
            if "wd" in client_beacon_types.get(key, ()):
                sig.append("webdriver")
            if args.beacon:
                hits = load_beacons.get(key + (norm_path(r["path"]),), ())
                if not any(-5 <= bt - r["epoch"] <= 120 for bt in hits):
                    sig.append("no_beacon")
                if not ({"int", "vis5"} & client_beacon_types.get(key, set())):
                    sig.append("no_interaction_all_day")
            chrom = CHROMIUM_RE.search(r["ua"])
            fox = FIREFOX_RE.search(r["ua"])
            if (chrom or fox) and not r.get("sfm"):
                sig.append("no_sec_fetch")
            if chrom and not r.get("chua"):
                sig.append("no_client_hints")
            if (chrom and int(chrom.group(1)) < args.min_chrome) or (fox and int(fox.group(1)) < args.min_firefox):
                sig.append("outdated_browser")
            if not r.get("al"):
                sig.append("no_accept_language")
            if r.get("acc", "") in ("", "*/*"):
                sig.append("generic_accept")
            if r["epoch"] > flags["first"] and not r.get("cs"):
                sig.append("no_cookie_on_repeat")
            if info["cloud"] or HOSTING_ORG_RE.search(info["org"] or ""):
                sig.append("datacenter_ip")
            if info["tor"]:
                sig.append("tor_exit")
            for name in ("high_rate", "few_assets", "regular_timing"):
                if flags[name]:
                    sig.append(name)
            if r["query"] and (SPAM_QUERY_RE.search(unquote(r["query"])) or len(r["query"]) > 200):
                sig.append("spam_query")
            if key in robots:
                sig.append("reads_robots_as_browser")

            score = min(100, sum(WEIGHTS[s] for s in sig))
            cls = "automated" if score >= AUTOMATED_AT else "uncertain" if score >= UNCERTAIN_AT else "human"
            if cls == "human" and r.get("auth") == "1":
                cls = "signed_in"
        else:
            score = 100 if cls != "verified_search_engine" else 0

        for s in sig:
            signal_counts[(r["day"], s)] += 1
        urt = sum(float(x) for x in re.findall(r"[\d.]+", r.get("urt", "")) or [0])
        agg = summary[(r["day"], r.get("host", ""), cls)]
        agg[0] += 1
        agg[1] += urt
        agg[2] += int(r.get("b", "0") or 0)
        day_totals[(r["day"], r.get("host", ""))] += 1
        h = ip_hash(r["ip"], salt)
        top_clients[(r["day"], cls, h, r["ip"], r["ua"])] += 1
        top_paths[(r["day"], cls, r["path"])] += 1
        if detail:
            detail.writerow([r["day"], r["time"].isoformat(), r.get("host", ""), r["path"], r.get("s", ""), cls, score,
                             "|".join(sig), h, info["asn"], info["org"], info["country"], info["cloud"], r["ua"],
                             RULES_VERSION])

    if detail_fh:
        detail_fh.close()

    with open(os.path.join(args.out, "daily_summary.csv"), "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["day", "host", "class", "page_views", "share_pct", "server_seconds", "bytes", "rules_version"])
        for (day, host, cls), (n, secs, b) in sorted(summary.items()):
            w.writerow([day, host, cls, n, round(100 * n / day_totals[(day, host)], 2), round(secs, 1), b, RULES_VERSION])

    with open(os.path.join(args.out, "signals.csv"), "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["day", "signal", "weight", "page_views"])
        for (day, s), n in sorted(signal_counts.items()):
            w.writerow([day, s, WEIGHTS[s], n])

    with open(os.path.join(args.out, "top_clients.csv"), "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["day", "class", "ip_hash", "asn", "org", "country", "cloud", "user_agent", "page_views"])
        ranked = collections.defaultdict(list)
        for (day, cls, h, ip, ua), n in top_clients.items():
            ranked[(day, cls)].append((n, h, ip, ua))
        for (day, cls), items in sorted(ranked.items()):
            for n, h, ip, ua in sorted(items, reverse=True)[:50]:
                i = enrich.lookup(ip)
                w.writerow([day, cls, h, i["asn"], i["org"], i["country"], i["cloud"], ua, n])

    with open(os.path.join(args.out, "top_paths.csv"), "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["day", "class", "path", "page_views"])
        ranked = collections.defaultdict(list)
        for (day, cls, p), n in top_paths.items():
            ranked[(day, cls)].append((n, p))
        for (day, cls), items in sorted(ranked.items()):
            for n, p in sorted(items, reverse=True)[:50]:
                w.writerow([day, cls, p, n])

    print(f"{page_count} page views from {len(files)} file(s) written to {args.out} (rules {RULES_VERSION})")


if __name__ == "__main__":
    main()
