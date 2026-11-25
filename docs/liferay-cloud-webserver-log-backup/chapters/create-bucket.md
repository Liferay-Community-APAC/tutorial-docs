---
title: 1. Create the S3 Bucket
parent: Chapters
nav_order: 1
---

# 1. Create the S3 Bucket
{: .no_toc }

1. TOC
{:toc}

## Goal

Create a private, encrypted S3 bucket whose lifecycle rules move logs to cheaper storage over time and delete them
when your retention period ends.

## Steps

1. Create the bucket, block all public access, and turn on default encryption:

    ```bash
    aws s3api create-bucket --bucket <BUCKET> --region <AWS_REGION> \
      --create-bucket-configuration LocationConstraint=<AWS_REGION>

    aws s3api put-public-access-block --bucket <BUCKET> \
      --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

    aws s3api put-bucket-encryption --bucket <BUCKET> \
      --server-side-encryption-configuration \
      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
    ```

1. Save this as `lifecycle.json` and set the day counts to match your retention policy. In this example, files stay
   in Standard storage for 30 days, move to Infrequent Access, then to Glacier after 90 days, and are deleted after
   400 days (about 13 months):

    ```json
    {
      "Rules": [{
        "ID": "liferay-log-retention",
        "Status": "Enabled",
        "Filter": { "Prefix": "liferay-cloud/" },
        "Transitions": [
          { "Days": 30, "StorageClass": "STANDARD_IA" },
          { "Days": 90, "StorageClass": "GLACIER" }
        ],
        "Expiration": { "Days": 400 }
      }]
    }
    ```

1. Apply it:

    ```bash
    aws s3api put-bucket-lifecycle-configuration --bucket <BUCKET> \
      --lifecycle-configuration file://lifecycle.json
    ```

{: .tip }
Files in Glacier take minutes to hours to restore before you can read them. If you often investigate incidents
older than 90 days, push the Glacier transition later or use Glacier Instant Retrieval (`GLACIER_IR`).

## Check

```bash
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-lifecycle-configuration --bucket <BUCKET>
```

All four public-access settings are `true`, the encryption rule shows `AES256`, and the lifecycle rule is `Enabled`.
