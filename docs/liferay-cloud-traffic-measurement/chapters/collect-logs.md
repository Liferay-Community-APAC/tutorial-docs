---
title: 3. Collect the Logs
parent: Chapters
nav_order: 3
---

# 3. Collect the Logs
{: .no_toc }

1. TOC
{:toc}

## Goal

Have each UTC day's webserver logs as files the classifier can read.

## Steps

1. **Recommended:** set up the [Back Up Liferay Cloud Webserver Logs](../../liferay-cloud-webserver-log-backup/)
   tutorial. It accepts both the default and the measurement log format, and writes 24 hourly `.log.gz` files per day
   to S3 under `…/year=YYYY/month=MM/day=DD/`. Download one day's files:

    ```bash
    aws s3 cp --recursive \
      s3://<BUCKET>/liferay-cloud/<PROJECT_ID>/webserver/year=2026/month=11/day=24/ logs/2026-11-24/
    ```

1. **For a quick trial without the backup**, fetch an hour or a day straight from Liferay Cloud with the CLI. Always
   pass both `--since` and `--until`, or `lcp log` never exits:

    ```bash
    mkdir -p logs/2026-11-24
    lcp log -p <PROJECT_ID> -s webserver --since "2026-11-24 00:00" --until "2026-11-25 00:00" \
      --limit 10000 < /dev/null | gzip > logs/2026-11-24/webserver-2026-11-24.log.gz
    ```

    Run it with `TZ=UTC` so the dates are read as UTC. Liferay Cloud keeps the logs for 30 days.

{: .note }
The classifier reads plain or `.gz` files, and ignores everything on a line before `tm=1`, so the CLI's own prefix
(time and instance) does no harm. Lines in the default format, from before you turned the measurement format on, are
skipped.

## Check

```bash
zcat logs/2026-11-24/*.gz | grep -c 'tm=1'
```

The count is well above zero, and roughly matches the day's traffic.
