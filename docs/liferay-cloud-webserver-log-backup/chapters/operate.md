---
title: 7. Run It Day to Day
parent: Chapters
nav_order: 7
---

# 7. Run It Day to Day
{: .no_toc }

1. TOC
{:toc}

## Goal

Know what to do when a run fails, how to search the logs, who should read them, and how the job copes with busy
sites.

## Failures and re-runs

GitHub emails the workflow owner when a scheduled run fails. For team alerting, enable the commented `notify` job at
the end of the workflow and point it at Slack, Teams or email.

If any hour fails, the run is marked as failed and the other hours carry on. Open that run and use **Re-run failed
jobs**: the re-run reuses the date fixed by the `plan` job, so it backs up the same day, for as long as those hours
are still inside Liferay Cloud's 30-day window. Starting a *new* run instead backs up the day before the new run.

If `lcp log` fails part-way, for example on a temporary API error, the script itself retries the hour up to 3 times,
60 seconds apart, before the job fails.

## Searching the logs

For one-off lookups, use `aws s3 cp` and `zgrep`. For regular analysis, define an Amazon Athena table over the bucket
prefix; the `year=/month=/day=` folders work as partitions, so a query for one day reads only that day's files.

## Access control

The logs contain client IP addresses and request URLs, which can be personal information under privacy law. Limit
read access to the bucket to the people who need it, and set the retention period to match your privacy policy.

## Credentials

When the service user's password changes, update the `LCP_PASSWORD` secret at the same time. A wrong password makes
every run fail at the *Authenticate LCP CLI* step.

## Large volumes

Each 10,000 lines costs one request plus a 3-second pause, on top of download time (measured at roughly 850 lines a
second). For example, at 11,000 lines a minute (about 16 million a day):

- One job for the whole day would need about 1,600 requests and an estimated 5 to 7 hours, beyond the 6-hour limit
  for a GitHub-hosted job.
- One hour is about 660,000 lines and 66 requests, an estimated 15 to 20 minutes per job. With 4 in parallel, the
  day finishes in roughly 1.5 to 2 hours.
- Expect about 500 MB of gzipped files a day in S3, and several GB of raw text passing through the runners.

These are estimates from a smaller environment. Measure the real run time in the go-live test, and raise
`max-parallel` only with Liferay Cloud support's agreement. For sustained volumes at this level, also consider
streaming the logs as they are written (below).

## Keeping non-access lines

The filter drops lines without an access-log timestamp, such as nginx warnings and startup messages. To keep those
too, upload the raw fetch as well (with some overlap between hours), or stream the logs.

## Optional: real-time streaming

For near real-time delivery to a log platform such as Splunk, Datadog or Elastic, nginx in the `webserver` service
can also send access logs over syslog, through a custom config file in the project repository:

```nginx
access_log syslog:server=logs.example.com:514,tag=liferay_web combined;
```

{: .warning }
nginx's syslog output uses UDP: lines can be lost and travel unencrypted. Send it to a forwarder inside the same
project (for example Vector or Fluent Bit as a custom service) that ships to your platform over TLS, and confirm with
Liferay Cloud support that the custom service and outbound traffic are allowed.

Streaming has no daily delay and doesn't depend on the 30-day window. Keep the S3 backup as an independent archive.

## Check

You know where failure alerts go, who can read the bucket, when the service user's password is next due to change,
and how long a full day's run takes on your environment.
