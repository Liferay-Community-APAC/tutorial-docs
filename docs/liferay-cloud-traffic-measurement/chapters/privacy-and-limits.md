---
title: 6. Privacy, Tuning and Limits
parent: Chapters
nav_order: 6
---

# 6. Privacy, Tuning and Limits
{: .no_toc }

1. TOC
{:toc}

## Goal

Know what personal data the measurement handles, how to tune the rules for your site, and what it can't tell you.

## Privacy

- The logs contain IP addresses, URLs, user agents and language preferences, which can be personal data. Limit who
  can read them, and agree the retention period with the site owner's privacy contact.
- The dashboard and summaries contain only salted IP hashes, which are still pseudonymous personal data. Rotate
  `TM_SALT`, for example monthly, so that visitors can't be linked across longer periods.
- `--detail` writes one row per page view. Use it for investigations only, and delete the file afterwards.
- MaxMind GeoLite2 requires an account and attribution when results are shared.

## Tuning

| Option | Default | When to change it |
| --- | --- | --- |
| `--min-chrome`, `--min-firefox` | 110 | Raise it as browsers move on, so old versions keep counting as outdated |
| `--rate-limit` | 30 | Page views a minute from one client counted as high. Raise it if real users browse very fast, for example on a catalogue |
| `AUTOMATED_AT`, `UNCERTAIN_AT` and `WEIGHTS` in `classify_traffic.py` | 60, 30 | If the uncertain share grows, look at `signals.csv` to see which signals put page views there |

Every output row carries the rules version, so a change in the rules shows up in the dashboard's header.

## Limits

- **Signed-in detection** relies on Liferay's `LFR_SESSION_STATE_` cookie. Confirm on your DXP version that it is set
  only for signed-in users and cleared at sign-out.
- **Few assets** can misfire if static files are served from a CDN or the browser cache.
- **Search engine verification** needs working reverse DNS where the classifier runs.
- **Cloud ranges:** Azure's ranges are published as a weekly file whose address changes; set
  `AZURE_SERVICE_TAGS_URL` for `fetch-enrichment.sh` to include them.
- **The page-view selection** (GET, status 200 or 304, HTML) is this tutorial's own definition. It is not guaranteed
  to match any page view count Liferay uses for subscriptions or billing.
- **Volume:** the classifier handled 200,000 lines in about 20 seconds; a site with millions of lines a day takes
  tens of minutes per day.

## Check

The site owner has agreed the retention period, `TM_SALT` is stored in a secret manager with a rotation date, and the
uncertain share in the dashboard is low and stable.
