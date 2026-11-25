---
title: Back Up Liferay Cloud Webserver Logs
nav_order: 1
description: Keep Liferay Cloud webserver (nginx) access logs beyond the 30-day retention window with a scheduled GitHub Actions job that writes one encrypted file per hour to Amazon S3.
---

# Back Up Liferay Cloud Webserver Logs
{: .no_toc }

Liferay Cloud keeps the `webserver` service's nginx access logs for a rolling 30 days. This tutorial sets up a
scheduled GitHub Actions job that copies them to an Amazon S3 bucket you own, one compressed file per UTC hour, so
you can keep them as long as your security, audit or compliance rules require. It is for Liferay Cloud (PaaS)
administrators and the AWS or DevOps engineers who work with them.

You can also [download this tutorial as a PDF](Liferay-Cloud-Webserver-Log-Backup-Guide.pdf).

1. TOC
{:toc}

## What You'll Build

Every day at 01:30 UTC, a GitHub Actions workflow backs up the previous UTC day:

| Step | What happens |
| --- | --- |
| **Plan** | A short job fixes "yesterday" once for the whole run. |
| **Fetch** | 24 jobs, a few at a time, each sign in with the Liferay Cloud CLI (`lcp`) and read one UTC hour of `webserver` logs. |
| **Filter and compress** | Each job keeps only the access-log lines stamped in its hour and gzips them. |
| **Store** | The file goes to your S3 bucket, encrypted, under `year=/month=/day=` folders, with lifecycle rules for cheaper storage and deletion. |

The result is one file per hour per environment, for example
`liferay-cloud/myproject-prd/webserver/year=2026/month=11/day=24/webserver-myproject-prd-2026-11-24T13.log.gz`,
ready for `zgrep` or Amazon Athena. GitHub authenticates to AWS with short-lived OIDC credentials, so no AWS keys are
stored anywhere.

Fetching each day as 24 hourly jobs keeps every job short, even for busy sites. At about 11,000 log lines a minute,
a single job for the whole day would run past GitHub's 6-hour limit; hourly jobs finish in an estimated 1.5 to 2
hours, 4 at a time.

## Before You Start

- **Liferay Cloud:** a Liferay Cloud (PaaS) project with a `webserver` service. Tested with Liferay Cloud CLI
  3.24.0 and the `liferaycloud/nginx:1.31.0-6.8.0` webserver image.
- **AWS:** an account where you can create an S3 bucket, an IAM role and an OpenID Connect identity provider, and
  the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
- **GitHub:** a repository with Actions enabled, where you can add secrets. It can be the Liferay Cloud project
  repository or a separate operations repository.
- **A Liferay Cloud service user:** a dedicated account that can view the target environment and has a Liferay Cloud
  password. Accounts created through SSO have none until one is set.
- **Time:** about two hours, plus a day for the first scheduled run.

Throughout the tutorial, replace these placeholders:

| Placeholder | Meaning | Example |
| --- | --- | --- |
| `<PROJECT_ID>` | Liferay Cloud environment ID, as shown in the console URL | `myproject-prd` |
| `<BUCKET>` | S3 bucket name (globally unique) | `acme-liferay-logs` |
| `<AWS_REGION>` | AWS region for the bucket | `ap-northeast-1` |
| `<ACCOUNT_ID>` | 12-digit AWS account ID | `123456789012` |
| `<ORG>/<REPO>` | GitHub organization and repository | `acme/liferay-ops` |

## Chapters

| Chapter | What you do |
| --- | --- |
| [1. Create the S3 Bucket](chapters/create-bucket.html) | A private, encrypted bucket with retention rules. |
| [2. Connect GitHub to AWS](chapters/connect-github-to-aws.html) | An OIDC identity provider and a role that can only upload logs. |
| [3. Sign In to Liferay Cloud](chapters/liferay-cloud-sign-in.html) | A service user the workflow can sign in with, unattended. |
| [4. Add the Backup Script](chapters/backup-script.html) | The script that fetches, filters, compresses and uploads one hour. |
| [5. Add the Workflow](chapters/workflow.html) | The scheduled workflow that runs the 24 hourly jobs. |
| [6. Test and Go Live](chapters/test-and-go-live.html) | A manual run, checks, and the go-live checklist. |
| [7. Run It Day to Day](chapters/operate.html) | Failures and re-runs, searching the logs, access, and large volumes. |

## Status

*Partly tested.* The Liferay Cloud CLI behaviour the script relies on was verified against a Liferay Cloud
development environment with CLI 3.24.0, and the script was run end to end in dry-run mode (no upload) on Ubuntu
24.04 against that environment, including all 24 hourly jobs. Not yet tested: the S3 upload and IAM role, the
password sign-in step, and the GitHub Actions matrix run itself. Run times at high volume are estimates until
measured on your environment.
