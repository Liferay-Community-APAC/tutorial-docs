#!/usr/bin/env python3
"""Build a self-contained HTML dashboard from classify_traffic.py output.

Usage:
  build_report.py --in out --out report.html [--in more_out ...] [--title "..."] [--note "..."]

Every daily_summary.csv, signals.csv, top_clients.csv and top_paths.csv found under
the --in folders is merged (a day processed twice keeps the last folder's numbers).
The HTML has no external dependencies, so it can be opened offline or attached to
an email. It contains only aggregates, salted IP hashes and user agents.
"""

import argparse
import csv
import datetime as dt
import glob
import json
import os
import sys


def read_csvs(folders, name):
    rows = []
    for folder in folders:
        for path in sorted(glob.glob(os.path.join(folder, "**", name), recursive=True)):
            with open(path, newline="") as fh:
                rows.extend(csv.DictReader(fh))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inputs", action="append", required=True, help="classifier output folder (repeatable)")
    ap.add_argument("--out", required=True, help="HTML file to write")
    ap.add_argument("--title", default="Website traffic: humans and automation")
    ap.add_argument("--note", default="", help="banner text, e.g. 'Sample data'")
    args = ap.parse_args()

    summary = {}
    for r in read_csvs(args.inputs, "daily_summary.csv"):
        summary[(r["day"], r["host"], r["class"])] = [r["day"], r["host"], r["class"], int(r["page_views"]),
                                                      float(r["server_seconds"]), int(r["bytes"])]
    if not summary:
        sys.exit("error: no daily_summary.csv found under " + ", ".join(args.inputs))
    signals = {}
    for r in read_csvs(args.inputs, "signals.csv"):
        signals[(r["day"], r["signal"])] = [r["day"], r["signal"], int(r["page_views"])]
    clients = {}
    for r in read_csvs(args.inputs, "top_clients.csv"):
        clients[(r["day"], r["class"], r["ip_hash"], r["user_agent"])] = [
            r["day"], r["class"], r["ip_hash"], r["org"], r["country"], r["cloud"], r["user_agent"], int(r["page_views"])]
    paths = {}
    for r in read_csvs(args.inputs, "top_paths.csv"):
        paths[(r["day"], r["class"], r["path"])] = [r["day"], r["class"], r["path"], int(r["page_views"])]
    rules = sorted({r["rules_version"] for r in read_csvs(args.inputs, "daily_summary.csv")})

    data = {
        "title": args.title,
        "note": args.note,
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rules": ", ".join(rules),
        "days": sorted({k[0] for k in summary}),
        "hosts": sorted({k[1] for k in summary}),
        "summary": list(summary.values()),
        "signals": list(signals.values()),
        "clients": list(clients.values()),
        "paths": list(paths.values()),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.replace("__TITLE__", args.title.replace("<", "&lt;")).replace("__DATA__", payload)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {args.out}: {len(data['days'])} day(s), {len(data['hosts'])} host(s)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10); --wash: rgba(11,11,11,0.04);
  --up-good: #006300; --down-bad: #b42f2f; --neutral-bar: #52514e;
  --c-human: #2a78d6; --c-signed: #eb6834; --c-uncertain: #1baf7a;
  --c-automated: #eda100; --c-declared: #e87ba4; --c-search: #008300;
  --note-bg: #fff4d6; --note-ink: #5a4300;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10); --wash: rgba(255,255,255,0.05);
    --up-good: #0ca30c; --down-bad: #e66767; --neutral-bar: #c3c2b7;
    --c-human: #3987e5; --c-signed: #d95926; --c-uncertain: #199e70;
    --c-automated: #c98500; --c-declared: #d55181; --c-search: #0ca30c;
    --note-bg: #3a2f10; --note-ink: #f5dfa0;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10); --wash: rgba(255,255,255,0.05);
  --up-good: #0ca30c; --down-bad: #e66767; --neutral-bar: #c3c2b7;
  --c-human: #3987e5; --c-signed: #d95926; --c-uncertain: #199e70;
  --c-automated: #c98500; --c-declared: #d55181; --c-search: #0ca30c;
  --note-bg: #3a2f10; --note-ink: #f5dfa0;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 24px 16px 48px; }
header h1 { font-size: 22px; margin: 0 0 4px; font-weight: 650; }
header .meta { color: var(--ink-2); font-size: 13px; }
.note { background: var(--note-bg); color: var(--note-ink); border-radius: 8px; padding: 8px 12px; margin: 14px 0 0; font-size: 13px; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 18px 0; }
.seg { display: inline-flex; background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; padding: 2px; }
.seg button { border: 0; background: none; color: var(--ink-2); font: inherit; font-size: 13px; padding: 5px 12px; border-radius: 6px; cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--wash); color: var(--ink); font-weight: 600; }
select { font: inherit; font-size: 13px; padding: 5px 8px; border-radius: 8px; border: 1px solid var(--ring); background: var(--surface); color: var(--ink); }
.range-label { color: var(--muted); font-size: 13px; margin-left: auto; }
.grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; }
.card { background: var(--surface); border: 1px solid var(--ring); border-radius: 12px; padding: 16px; min-width: 0; }
.card h2 { font-size: 14px; font-weight: 600; margin: 0 0 2px; }
.card .sub { color: var(--ink-2); font-size: 12.5px; margin: 0 0 12px; }
.hero { grid-column: span 4; display: flex; flex-direction: column; justify-content: center; }
.hero .label, .tile .label { color: var(--ink-2); font-size: 13px; }
.hero .value { font-size: 52px; font-weight: 650; line-height: 1.05; margin: 6px 0; }
.tiles { grid-column: span 8; display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.tile .value { font-size: 26px; font-weight: 600; margin: 4px 0 2px; }
.delta { font-size: 12.5px; color: var(--ink-2); }
.delta.good { color: var(--up-good); } .delta.bad { color: var(--down-bad); }
.span-12 { grid-column: span 12; } .span-8 { grid-column: span 8; } .span-6 { grid-column: span 6; } .span-4 { grid-column: span 4; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12.5px; color: var(--ink-2); margin: 0 0 8px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.sw { width: 10px; height: 10px; border-radius: 3px; display: inline-block; flex: none; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
svg text { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.tip { position: fixed; pointer-events: none; background: var(--surface); color: var(--ink); border: 1px solid var(--ring); border-radius: 8px;
       box-shadow: 0 4px 16px rgba(0,0,0,0.12); padding: 8px 10px; font-size: 12.5px; z-index: 10; display: none; min-width: 170px; }
.tip .t { font-weight: 600; margin-bottom: 4px; }
.tip .r { display: flex; align-items: center; gap: 6px; justify-content: space-between; }
.tip .r .k { display: inline-flex; align-items: center; gap: 6px; color: var(--ink-2); }
.tip .r .v { font-variant-numeric: tabular-nums; }
.segbar { display: flex; gap: 2px; height: 28px; margin: 6px 0 10px; }
.segbar div { border-radius: 4px; color: #fff; font-size: 12px; font-weight: 600; display: flex; align-items: center; padding-left: 6px; white-space: nowrap; overflow: hidden; min-width: 0; }
.segbar div.dark-ink { color: #0b0b0b; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
th { text-align: left; color: var(--ink-2); font-weight: 600; border-bottom: 1px solid var(--axis); padding: 6px 8px; white-space: nowrap; }
td { border-bottom: 1px solid var(--grid); padding: 6px 8px; vertical-align: top; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
td.ua { color: var(--ink-2); max-width: 340px; overflow-wrap: anywhere; }
td.path { overflow-wrap: anywhere; }
.cls { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.scroll { overflow-x: auto; }
details summary { cursor: pointer; color: var(--ink-2); font-size: 13px; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; margin: 0; font-size: 13px; }
dt { font-weight: 600; display: flex; align-items: center; gap: 6px; } dd { margin: 0; color: var(--ink-2); }
.empty { color: var(--muted); font-size: 13px; padding: 12px 0; }
@media (max-width: 900px) {
  .hero, .tiles, .span-8, .span-6, .span-4 { grid-column: span 12; }
  .tiles { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) { .hero .value { font-size: 44px; } .range-label { margin-left: 0; width: 100%; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1 id="title"></h1>
    <div class="meta" id="meta"></div>
    <div class="note" id="note" hidden></div>
  </header>

  <div class="filters">
    <div class="seg" role="group" aria-label="Date range" id="ranges"></div>
    <select id="host" aria-label="Host" hidden></select>
    <span class="range-label" id="rangeLabel"></span>
  </div>

  <div class="grid">
    <div class="card hero">
      <div class="label">Human page views</div>
      <div class="value" id="heroValue"></div>
      <div class="delta" id="heroDelta"></div>
      <div class="delta" id="heroSub" style="margin-top:6px"></div>
    </div>
    <div class="tiles" id="tiles"></div>

    <div class="card span-12">
      <h2>Page views per day, by class</h2>
      <p class="sub">Each column is one UTC day. Hover a column for the breakdown.</p>
      <div class="legend" id="legendStack"></div>
      <div id="stack"></div>
    </div>

    <div class="card span-6">
      <h2>Share of page views: humans vs automation</h2>
      <p class="sub">Humans includes signed-in users. Automation is automated plus scripts and headless browsers.</p>
      <div class="legend" id="legendShare"></div>
      <div id="share"></div>
    </div>

    <div class="card span-6">
      <h2>Where Liferay's page processing time goes</h2>
      <p class="sub">Total backend response time for page views in the period, by class.</p>
      <div id="segbar"></div>
      <div class="legend" id="legendSeg"></div>
      <div id="segTable"></div>
    </div>

    <div class="card span-6">
      <h2>Why page views were flagged</h2>
      <p class="sub">Page views on which each signal fired (one page view can trigger several).</p>
      <div id="signals"></div>
    </div>

    <div class="card span-6">
      <h2>Pages most targeted by automation</h2>
      <p class="sub">Page views from automated clients, scripts and headless browsers.</p>
      <div class="scroll" id="paths"></div>
    </div>

    <div class="card span-12">
      <h2>Top automated clients</h2>
      <p class="sub">Candidates for blocking or rate limiting. Clients are identified by a salted IP hash plus user agent; totals are summed from each day's top 50, so they can be slightly low.</p>
      <div class="scroll" id="clients"></div>
    </div>

    <div class="card span-12">
      <details>
        <summary>Daily numbers (table view)</summary>
        <div class="scroll" id="dailyTable" style="margin-top:10px"></div>
      </details>
    </div>

    <div class="card span-12">
      <h2>What the classes mean</h2>
      <p class="sub">Only GET responses with status 200 or 304 and an HTML content type count as page views.</p>
      <dl id="defs"></dl>
    </div>
  </div>
</div>
<div class="tip" id="tip" role="tooltip"></div>

<script>
const DATA = __DATA__;

const GROUPS = [
  { id: "human", label: "Human", color: "--c-human", classes: ["human"], desc: "Passed every bot check. Real visitors." },
  { id: "signed", label: "Signed in", color: "--c-signed", classes: ["signed_in"], desc: "Passed every bot check and carried a Liferay signed-in cookie." },
  { id: "uncertain", label: "Uncertain", color: "--c-uncertain", classes: ["uncertain"], desc: "Some bot signals, not enough to decide (score 30–59). Watch this share: if it grows, the rules need tuning.", ink: "#0b0b0b" },
  { id: "automated", label: "Automated", color: "--c-automated", classes: ["automated", "script_or_headless"], desc: "Score 60 or more, or a user agent of an HTTP library or headless browser. Bots that do not identify themselves.", ink: "#0b0b0b" },
  { id: "declared", label: "Declared bots", color: "--c-declared", classes: ["declared_bot"], desc: "Say they are bots (SEO, AI and monitoring crawlers), or claim to be a search engine that could not be verified." },
  { id: "search", label: "Search engines", color: "--c-search", classes: ["verified_search_engine"], desc: "Googlebot, Bingbot and others, confirmed by reverse and forward DNS." },
];
const CLASS_GROUP = {}; GROUPS.forEach(g => g.classes.forEach(c => CLASS_GROUP[c] = g));
const CLASS_LABEL = { human: "Human", signed_in: "Signed in", uncertain: "Uncertain", automated: "Automated",
  script_or_headless: "Script / headless", declared_bot: "Declared bot", verified_search_engine: "Search engine" };
const SIGNAL_LABEL = {
  fake_search_engine: "Claims to be a search engine, DNS says no", honeypot: "Requested the hidden honeypot link",
  webdriver: "Browser reports automation (webdriver)", no_beacon: "Page loaded without the page beacon",
  no_interaction_all_day: "No scroll, click or key all day", no_sec_fetch: "Browser headers missing (Sec-Fetch)",
  no_client_hints: "Chrome without client hints", no_accept_language: "No Accept-Language header",
  generic_accept: "Generic Accept header", no_cookie_on_repeat: "No cookie on repeat visit",
  datacenter_ip: "Cloud or hosting provider address", tor_exit: "Tor exit node", high_rate: "More than 30 pages a minute",
  few_assets: "Loads pages but not their CSS/JS/images", regular_timing: "Machine-regular timing",
  spam_query: "Spam in the query string", outdated_browser: "Outdated browser version", reads_robots_as_browser: "Browser that reads robots.txt",
};
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = n => n.toLocaleString("en-US");
const compact = n => n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M" : n >= 1e4 ? Math.round(n / 1e3) + "K" : n >= 1e3 ? (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K" : String(n);
const pct = (a, b) => b ? 100 * a / b : 0;
const pctTxt = v => (v >= 10 ? v.toFixed(0) : v.toFixed(1)) + "%";
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const dayLabel = d => new Date(d + "T00:00:00Z").toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }

const state = { range: Math.min(30, DATA.days.length), host: "" };
const RANGES = [7, 14, 30, 90].filter(r => r < DATA.days.length).map(r => ({ n: r, label: `Last ${r} days` }))
  .concat([{ n: DATA.days.length, label: DATA.days.length === 1 ? "1 day" : `All ${DATA.days.length} days` }]);

// ---------- data shaping ----------
function daysInRange(offset = 0) {
  const all = DATA.days, end = all.length - offset * state.range;
  return all.slice(Math.max(0, end - state.range), Math.max(0, end));
}
function groupTotals(days) {
  const set = new Set(days), per = {}, secs = {};
  days.forEach(d => { per[d] = {}; GROUPS.forEach(g => per[d][g.id] = 0); });
  GROUPS.forEach(g => secs[g.id] = 0);
  for (const [d, h, c, v, s] of DATA.summary) {
    if (!set.has(d) || (state.host && h !== state.host)) continue;
    const g = CLASS_GROUP[c]; if (!g) continue;
    per[d][g.id] += v; secs[g.id] += s;
  }
  const tot = {}; GROUPS.forEach(g => tot[g.id] = days.reduce((a, d) => a + per[d][g.id], 0));
  return { per, tot, secs, all: Object.values(tot).reduce((a, b) => a + b, 0) };
}

// ---------- tooltip ----------
const tip = document.getElementById("tip");
function showTip(ev, html) {
  tip.innerHTML = html; tip.style.display = "block";
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
const hideTip = () => tip.style.display = "none";
const sw = g => `<span class="sw" style="background:var(${g.color})"></span>`;

// ---------- header, filters ----------
function header() {
  document.getElementById("title").textContent = DATA.title;
  document.getElementById("meta").textContent =
    `${DATA.hosts.join(", ")} · ${dayLabel(DATA.days[0])} – ${dayLabel(DATA.days.at(-1))} (UTC days) · rules ${DATA.rules} · generated ${DATA.generated}`;
  if (DATA.note) { const n = document.getElementById("note"); n.textContent = DATA.note; n.hidden = false; }
  const rg = document.getElementById("ranges");
  RANGES.forEach(r => {
    const b = document.createElement("button");
    b.textContent = r.label;
    b.onclick = () => { state.range = r.n; render(); };
    b.dataset.r = r.n; rg.appendChild(b);
  });
  if (DATA.hosts.length > 1) {
    const s = document.getElementById("host"); s.hidden = false;
    s.innerHTML = `<option value="">All hosts</option>` + DATA.hosts.map(h => `<option>${esc(h)}</option>`).join("");
    s.onchange = () => { state.host = s.value; render(); };
  }
}

// ---------- tiles ----------
function deltaHtml(cur, prev, upIsGood, isPct) {
  if (prev === null) return `<span>No previous period to compare</span>`;
  const diff = isPct ? cur - prev : pct(cur - prev, prev);
  if (!isFinite(diff)) return "";
  const up = diff > 0, flat = Math.abs(diff) < 0.05;
  const cls = flat ? "" : (up === upIsGood ? "good" : "bad");
  const arrow = flat ? "→" : up ? "▲" : "▼";
  const txt = isPct ? `${Math.abs(diff).toFixed(1)} pts` : `${Math.abs(diff).toFixed(1)}%`;
  return `<span class="delta ${cls}">${arrow} ${txt}</span> <span class="delta">vs previous ${state.range} days</span>`;
}
function tiles(cur, prev) {
  const humans = t => t.tot.human + t.tot.signed;
  const autoShare = t => pct(t.tot.automated, t.all);
  const botsShare = t => pct(t.tot.declared + t.tot.search, t.all);
  const uncShare = t => pct(t.tot.uncertain, t.all);
  const secAll = t => Object.values(t.secs).reduce((a, b) => a + b, 0);
  const autoTime = t => pct(t.secs.automated, secAll(t));
  document.getElementById("heroValue").textContent = fmt(humans(cur));
  document.getElementById("heroDelta").innerHTML = deltaHtml(humans(cur), prev ? humans(prev) : null, true, false);
  document.getElementById("heroSub").textContent = `${pctTxt(pct(humans(cur), cur.all))} of all ${fmt(cur.all)} page views`;
  const defs = [
    ["Automated share", pctTxt(autoShare(cur)), prev ? deltaHtml(autoShare(cur), autoShare(prev), false, true) : deltaHtml(0, null)],
    ["Backend time used by automation", pctTxt(autoTime(cur)), prev ? deltaHtml(autoTime(cur), autoTime(prev), false, true) : deltaHtml(0, null)],
    ["Identified bots and search engines", pctTxt(botsShare(cur)), prev ? deltaHtml(botsShare(cur), botsShare(prev), false, true) : deltaHtml(0, null)],
    ["Uncertain (data quality)", pctTxt(uncShare(cur)), prev ? deltaHtml(uncShare(cur), uncShare(prev), false, true) : deltaHtml(0, null)],
  ];
  document.getElementById("tiles").innerHTML = defs.map(([l, v, d]) =>
    `<div class="card tile"><div class="label">${l}</div><div class="value">${v}</div><div>${d}</div></div>`).join("");
}

function legend(id, groups) {
  document.getElementById(id).innerHTML = groups.map(g => `<span>${sw(g)}${g.label}</span>`).join("");
}
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p; return 10 * p; }

// ---------- stacked columns ----------
function stack(days, t) {
  const host = document.getElementById("stack"); host.innerHTML = "";
  const W = Math.max(host.clientWidth, 320), H = 280, L = 44, R = 8, T = 8, B = 26;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Page views per day by class, stacked columns" }, host);
  const totals = days.map(d => GROUPS.reduce((a, g) => a + t.per[d][g.id], 0));
  const max = niceMax(Math.max(...totals, 1));
  const y = v => T + (H - T - B) * (1 - v / max);
  for (let i = 0; i <= 4; i++) {
    const v = max * i / 4, yy = y(v);
    el("line", { x1: L, x2: W - R, y1: yy, y2: yy, stroke: i ? css("--grid") : css("--axis"), "stroke-width": 1 }, svg);
    el("text", { x: L - 6, y: yy + 4, "text-anchor": "end" }, svg).textContent = compact(v);
  }
  const band = (W - L - R) / days.length, bw = Math.min(24, band * 0.7);
  const every = Math.ceil(days.length / Math.max(1, Math.floor((W - L - R) / 56)));
  days.forEach((d, i) => {
    const x = L + band * i + (band - bw) / 2;
    let acc = 0;
    const segs = GROUPS.filter(g => t.per[d][g.id] > 0);
    segs.forEach((g, k) => {
      const v = t.per[d][g.id], y0 = y(acc), y1 = y(acc + v);
      const gap = k > 0 ? 2 : 0, top = k === segs.length - 1;
      const h = Math.max(0, y0 - y1 - gap);
      if (h > 0) {
        if (top) {
          const r = Math.min(4, h, bw / 2);
          el("path", { d: `M${x},${y0 - gap} V${y1 + r} Q${x},${y1} ${x + r},${y1} H${x + bw - r} Q${x + bw},${y1} ${x + bw},${y1 + r} V${y0 - gap} Z`, fill: css(g.color) }, svg);
        } else el("rect", { x, y: y1, width: bw, height: h, fill: css(g.color) }, svg);
      }
      acc += v;
    });
    if (i % every === 0 || i === days.length - 1 && days.length < 20)
      el("text", { x: x + bw / 2, y: H - 8, "text-anchor": "middle" }, svg).textContent = dayLabel(d);
    const hit = el("rect", { x: L + band * i, y: T, width: band, height: H - T - B, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", ev => {
      const rows = GROUPS.slice().reverse().filter(g => t.per[d][g.id] > 0).map(g =>
        `<div class="r"><span class="k">${sw(g)}${g.label}</span><span class="v">${fmt(t.per[d][g.id])} · ${pctTxt(pct(t.per[d][g.id], totals[i]))}</span></div>`).join("");
      showTip(ev, `<div class="t">${dayLabel(d)} · ${fmt(totals[i])} page views</div>${rows}`);
      hit.setAttribute("fill", css("--wash"));
    });
    hit.addEventListener("mouseleave", () => { hideTip(); hit.setAttribute("fill", "transparent"); });
  });
}

// ---------- share lines ----------
function share(days, t) {
  const host = document.getElementById("share"); host.innerHTML = "";
  const W = Math.max(host.clientWidth, 300), H = 220, L = 40, R = 64, T = 10, B = 26;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Share of page views from humans and automation per day" }, host);
  const series = [
    { g: GROUPS[0], label: "Humans", v: days.map(d => { const a = GROUPS.reduce((s, g) => s + t.per[d][g.id], 0); return pct(t.per[d].human + t.per[d].signed, a); }) },
    { g: GROUPS[3], label: "Automation", v: days.map(d => { const a = GROUPS.reduce((s, g) => s + t.per[d][g.id], 0); return pct(t.per[d].automated, a); }) },
  ];
  document.getElementById("legendShare").innerHTML = series.map(s => `<span>${sw(s.g)}${s.label}</span>`).join("");
  const max = niceMax(Math.max(...series.flatMap(s => s.v), 10));
  const x = i => L + (W - L - R) * (days.length > 1 ? i / (days.length - 1) : 0.5);
  const y = v => T + (H - T - B) * (1 - v / max);
  for (let i = 0; i <= 4; i++) {
    const v = max * i / 4, yy = y(v);
    el("line", { x1: L, x2: W - R, y1: yy, y2: yy, stroke: i ? css("--grid") : css("--axis"), "stroke-width": 1 }, svg);
    el("text", { x: L - 6, y: yy + 4, "text-anchor": "end" }, svg).textContent = Math.round(v) + "%";
  }
  const every = Math.ceil(days.length / Math.max(1, Math.floor((W - L - R) / 56)));
  days.forEach((d, i) => { if (i % every === 0) el("text", { x: x(i), y: H - 8, "text-anchor": "middle" }, svg).textContent = dayLabel(d); });
  const ends = [];
  series.forEach(s => {
    el("path", { d: s.v.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(""), fill: "none", stroke: css(s.g.color), "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    const i = s.v.length - 1;
    el("circle", { cx: x(i), cy: y(s.v[i]), r: 4, fill: css(s.g.color), stroke: css("--surface"), "stroke-width": 2 }, svg);
    ends.push({ y: y(s.v[i]), txt: pctTxt(s.v[i]) });
  });
  ends.sort((a, b) => a.y - b.y);
  if (ends.length === 2 && ends[1].y - ends[0].y < 14) { ends[0].y -= 7; ends[1].y += 7; }
  ends.forEach(e => { const t = el("text", { x: W - R + 10, y: e.y + 4 }, svg); t.textContent = e.txt; t.style.fill = css("--ink"); });
  const cross = el("line", { x1: 0, x2: 0, y1: T, y2: H - B, stroke: css("--axis"), "stroke-width": 1, visibility: "hidden" }, svg);
  const hit = el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, fill: "transparent" }, svg);
  hit.addEventListener("mousemove", ev => {
    const r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * W / r.width;
    const i = Math.max(0, Math.min(days.length - 1, Math.round((px - L) / ((W - L - R) / Math.max(1, days.length - 1)))));
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
    showTip(ev, `<div class="t">${dayLabel(days[i])}</div>` + series.map(s =>
      `<div class="r"><span class="k">${sw(s.g)}${s.label}</span><span class="v">${pctTxt(s.v[i])}</span></div>`).join(""));
  });
  hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("visibility", "hidden"); });
}

// ---------- segmented bar: backend time ----------
function segbar(t) {
  const total = Object.values(t.secs).reduce((a, b) => a + b, 0);
  const box = document.getElementById("segbar"); box.innerHTML = "";
  const bar = document.createElement("div"); bar.className = "segbar"; bar.setAttribute("role", "img");
  bar.setAttribute("aria-label", "Backend time by class: " + GROUPS.map(g => `${g.label} ${pctTxt(pct(t.secs[g.id], total))}`).join(", "));
  GROUPS.forEach(g => {
    const v = t.secs[g.id]; if (v <= 0) return;
    const p = pct(v, total), d = document.createElement("div");
    d.style.flex = `${v} 1 0`; d.style.background = `var(${g.color})`; if (g.ink) d.classList.add("dark-ink");
    d.textContent = p >= 9 ? pctTxt(p) : "";
    d.addEventListener("mousemove", ev => showTip(ev, `<div class="t">${sw(g)} ${g.label}</div><div class="r"><span class="k">Backend time</span><span class="v">${fmtHours(v)}</span></div><div class="r"><span class="k">Share</span><span class="v">${pctTxt(p)}</span></div>`));
    d.addEventListener("mouseleave", hideTip);
    bar.appendChild(d);
  });
  box.appendChild(bar);
  legend("legendSeg", GROUPS.filter(g => t.secs[g.id] > 0));
  const pv = t.tot;
  document.getElementById("segTable").innerHTML = `<table><thead><tr><th>Class</th><th class="n">Page views</th><th class="n">Backend time</th><th class="n">Avg per page</th></tr></thead><tbody>` +
    GROUPS.map(g => `<tr><td><span class="cls">${sw(g)}${g.label}</span></td><td class="n">${fmt(pv[g.id])}</td><td class="n">${fmtHours(t.secs[g.id])}</td><td class="n">${pv[g.id] ? (1000 * t.secs[g.id] / pv[g.id]).toFixed(0) + " ms" : "–"}</td></tr>`).join("") + `</tbody></table>`;
}
function fmtHours(s) { return s >= 3600 ? (s / 3600).toFixed(1) + " h" : s >= 60 ? (s / 60).toFixed(0) + " min" : s.toFixed(0) + " s"; }

// ---------- signals ----------
function signals(days) {
  const set = new Set(days), tot = {};
  for (const [d, s, v] of DATA.signals) if (set.has(d)) tot[s] = (tot[s] || 0) + v;
  const rows = Object.entries(tot).sort((a, b) => b[1] - a[1]).slice(0, 12);
  const host = document.getElementById("signals"); host.innerHTML = "";
  if (!rows.length) { host.innerHTML = `<div class="empty">No signals fired in this period.</div>`; return; }
  const W = Math.max(host.clientWidth, 300), rowH = 26, labelW = Math.min(250, W * 0.5), H = rows.length * rowH + 4, R = 56;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Signals by number of page views flagged" }, host);
  const max = Math.max(...rows.map(r => r[1]));
  rows.forEach(([s, v], i) => {
    const yy = i * rowH + 4, w = Math.max(2, (W - labelW - R) * v / max), x0 = labelW;
    const lt = el("text", { x: labelW - 8, y: yy + 13, "text-anchor": "end" }, svg); lt.textContent = SIGNAL_LABEL[s] || s; lt.style.fill = css("--ink-2");
    const r = Math.min(4, w / 2);
    el("path", { d: `M${x0},${yy + 3} H${x0 + w - r} Q${x0 + w},${yy + 3} ${x0 + w},${yy + 3 + r} V${yy + 17 - r} Q${x0 + w},${yy + 17} ${x0 + w - r},${yy + 17} H${x0} Z`, fill: css("--neutral-bar") }, svg);
    const vt = el("text", { x: x0 + w + 6, y: yy + 14 }, svg); vt.textContent = compact(v); vt.style.fill = css("--ink");
    const hit = el("rect", { x: 0, y: yy, width: W, height: rowH, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", ev => showTip(ev, `<div class="t">${esc(SIGNAL_LABEL[s] || s)}</div><div class="r"><span class="k">Page views flagged</span><span class="v">${fmt(v)}</span></div><div class="r"><span class="k">Signal id</span><span class="v">${s}</span></div>`));
    hit.addEventListener("mouseleave", hideTip);
  });
}

// ---------- tables ----------
const AUTO = new Set(["automated", "script_or_headless"]);
function paths(days) {
  const set = new Set(days), tot = {};
  for (const [d, c, p, v] of DATA.paths) if (set.has(d) && AUTO.has(c)) tot[p] = (tot[p] || 0) + v;
  const rows = Object.entries(tot).sort((a, b) => b[1] - a[1]).slice(0, 12);
  const all = Object.values(tot).reduce((a, b) => a + b, 0);
  document.getElementById("paths").innerHTML = rows.length ? `<table><thead><tr><th>Page</th><th class="n">Automated views</th><th class="n">Share</th></tr></thead><tbody>` +
    rows.map(([p, v]) => `<tr><td class="path">${esc(decodePath(p))}</td><td class="n">${fmt(v)}</td><td class="n">${pctTxt(pct(v, all))}</td></tr>`).join("") + `</tbody></table>`
    : `<div class="empty">No automated page views in this period.</div>`;
}
function decodePath(p) { try { return decodeURIComponent(p); } catch (e) { return p; } }
function clients(days) {
  const set = new Set(days), tot = {};
  for (const [d, c, h, org, country, cloud, ua, v] of DATA.clients) {
    if (!set.has(d) || !AUTO.has(c)) continue;
    const k = h + "\u0000" + ua;
    if (!tot[k]) tot[k] = { h, ua, org, country, cloud, c, v: 0, days: new Set() };
    tot[k].v += v; tot[k].days.add(d);
  }
  const rows = Object.values(tot).sort((a, b) => b.v - a.v).slice(0, 15);
  document.getElementById("clients").innerHTML = rows.length ? `<table><thead><tr><th>Class</th><th>Client (IP hash)</th><th>Network</th><th>User agent</th><th class="n">Days seen</th><th class="n">Page views</th></tr></thead><tbody>` +
    rows.map(r => { const g = CLASS_GROUP[r.c]; const net = [r.cloud, r.org, r.country].filter(Boolean).join(" · ") || "–";
      return `<tr><td><span class="cls">${sw(g)}${CLASS_LABEL[r.c]}</span></td><td><code>${esc(r.h)}</code></td><td>${esc(net)}</td><td class="ua">${esc(r.ua || "(none)")}</td><td class="n">${r.days.size}</td><td class="n">${fmt(r.v)}</td></tr>`; }).join("") + `</tbody></table>`
    : `<div class="empty">No automated clients in this period.</div>`;
}
function dailyTable(days, t) {
  document.getElementById("dailyTable").innerHTML = `<table><thead><tr><th>Day (UTC)</th>${GROUPS.map(g => `<th class="n"><span class="cls">${sw(g)}${g.label}</span></th>`).join("")}<th class="n">Total</th></tr></thead><tbody>` +
    days.slice().reverse().map(d => { const tot = GROUPS.reduce((a, g) => a + t.per[d][g.id], 0);
      return `<tr><td>${d}</td>${GROUPS.map(g => `<td class="n">${fmt(t.per[d][g.id])}</td>`).join("")}<td class="n">${fmt(tot)}</td></tr>`; }).join("") + `</tbody></table>`;
}
function defs() {
  document.getElementById("defs").innerHTML = GROUPS.map(g => `<dt>${sw(g)}${g.label}</dt><dd>${g.desc}</dd>`).join("");
}

function render() {
  document.querySelectorAll("#ranges button").forEach(b => b.setAttribute("aria-pressed", String(+b.dataset.r === state.range)));
  const days = daysInRange(0), prevDays = daysInRange(1);
  const cur = groupTotals(days), prev = prevDays.length === state.range ? groupTotals(prevDays) : null;
  document.getElementById("rangeLabel").textContent = `${dayLabel(days[0])} – ${dayLabel(days.at(-1))}`;
  tiles(cur, prev);
  legend("legendStack", GROUPS);
  stack(days, cur); share(days, cur); segbar(cur); signals(days); paths(days); clients(days); dailyTable(days, cur);
}
header(); defs(); render();
addEventListener("load", render);   // re-measure once fonts and layout have settled
let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(render, 150); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
