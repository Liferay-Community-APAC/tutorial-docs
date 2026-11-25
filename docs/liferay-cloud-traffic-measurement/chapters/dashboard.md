---
title: 5. Build the Dashboard
parent: Chapters
nav_order: 5
---

# 5. Build the Dashboard
{: .no_toc }

1. TOC
{:toc}

## Goal

Turn the classifier's results into a single HTML dashboard you can open offline or attach to an email.

## Steps

1. Download [build_report.py](files/scripts/build_report.py) into the `scripts/` folder.
1. Build the dashboard from all the days classified so far. `--in` is searched recursively, so one folder per day
   works, and it can be repeated:

    ```bash
    python3 scripts/build_report.py --in out --out report.html \
      --title "www.example.com: humans and automation"
    ```

1. Open `report.html` in a browser. It has no external dependencies, and contains only totals, salted IP hashes and
   user agents.

See the [sample dashboard](files/samples/sample-report.html), built from 30 days of synthetic traffic. To rebuild it
yourself, run [make_sample_logs.py](files/samples/make_sample_logs.py) with AWS's `ip-ranges.json`, then the
classifier and `build_report.py`.

## Reading it

Choose the last 7, 14 or 30 days at the top. Where the data covers the previous period too, each figure shows the
change against it, coloured by whether the change is good.

| Section | Question it answers |
| --- | --- |
| Human page views (headline) | How much real traffic does the site get, and is it growing? |
| Automated share | How much of the traffic is bots that don't identify themselves? |
| Backend time used by automation | How much of Liferay's page processing goes to bots? Bots often hit expensive pages such as search, so this can be well above their share of page views. |
| Identified bots and search engines | How much comes from crawlers that announce themselves? |
| Uncertain (data quality) | Can the numbers be trusted? If this share grows, the rules need tuning. |
| Page views per day, by class | When did bot traffic spike? Hover a column for the day's breakdown. |
| Humans vs automation share | Is the mix changing over time? |
| Where page processing time goes | Backend time and average time per page, by class |
| Why page views were flagged | Which signals drive the results |
| Pages most targeted by automation | What are bots after? |
| Top automated clients | Candidates for blocking or rate limiting: cloud provider, user agent, days seen |
| Daily numbers | The same data as a table |

{: .note }
The top clients are summed from each day's top 50, so their totals can be slightly low. The network column shows
the cloud provider; with MaxMind GeoLite2 set up it also shows the network owner and country.

## Check

The dashboard's date range matches the days you classified, and its human page views for a day match the sum of the
`human` and `signed_in` rows in that day's `daily_summary.csv`.
