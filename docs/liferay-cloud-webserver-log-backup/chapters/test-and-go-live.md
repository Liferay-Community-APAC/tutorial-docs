---
title: 6. Test and Go Live
parent: Chapters
nav_order: 6
---

# 6. Test and Go Live
{: .no_toc }

1. TOC
{:toc}

## Goal

Run the workflow once by hand, confirm the files are complete, and go through the go-live checklist.

## Steps

1. In GitHub, open **Actions → Backup Liferay Cloud webserver logs → Run workflow**.
1. Confirm all 24 hourly jobs succeed. Each job's log ends with `Uploaded N lines ...`, and the line before it shows
   the first and last timestamps kept.
1. Check that 24 files exist in S3:

    ```bash
    aws s3 ls s3://<BUCKET>/liferay-cloud/<PROJECT_ID>/webserver/year=YYYY/month=MM/day=DD/
    ```

    Your own AWS user needs read access for this; the workflow's role can only upload.

1. Download one file and spot-check that its first and last lines fall in the expected UTC hour (HH:00 to HH:59):

    ```bash
    aws s3 cp s3://<BUCKET>/liferay-cloud/<PROJECT_ID>/webserver/year=YYYY/month=MM/day=DD/webserver-<PROJECT_ID>-YYYY-MM-DDT13.log.gz .
    zcat webserver-*-T13.log.gz | head -1
    zcat webserver-*-T13.log.gz | tail -1
    ```

1. **Check completeness:** for a busy hour, compare the number of lines in that hour's file (`zcat … | wc -l`) with
   what the Liferay Cloud console shows for the same hour.
1. **Check run time:** note how long the slowest *Back up hour* step takes and how long the whole run takes, and
   compare with [Large volumes](operate.html#large-volumes).

{: .note }
The workflow only ever backs up the previous day. Days before go-live that are still inside the 30-day window are
not copied. If you need them, export them before they expire.

## Go-live checklist

- [ ] S3 bucket created: public access blocked, default encryption on, lifecycle rule matches the retention policy
- [ ] GitHub OIDC provider and IAM role created; the role allows `s3:PutObject` on the log prefix only
- [ ] Secrets `AWS_ROLE_ARN`, `LCP_USER` and `LCP_PASSWORD` saved in the repository
- [ ] Service user has a Liferay Cloud password with no spaces, and can see the target environment
- [ ] Manual test run succeeded, and line counts for a busy hour match the console
- [ ] All 24 hourly files present for the test day; run time checked against the environment's volume
- [ ] `max-parallel` agreed with Liferay Cloud support if raised above 4
- [ ] Failure notifications reach the operations team, and the team knows to use **Re-run failed jobs**

## Check

The next morning, the scheduled 01:30 UTC run has succeeded on its own and the previous day's 24 files are in S3.
