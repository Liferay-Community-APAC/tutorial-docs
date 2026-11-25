---
title: 2. Connect GitHub to AWS
parent: Chapters
nav_order: 2
---

# 2. Connect GitHub to AWS
{: .no_toc }

1. TOC
{:toc}

## Goal

Let the workflow upload to the bucket with short-lived credentials from GitHub's OpenID Connect (OIDC) integration,
through a role that can do nothing else. No access keys are stored anywhere.

## Steps

1. In **IAM → Identity providers**, add an OpenID Connect provider with the URL
   `https://token.actions.githubusercontent.com` and the audience `sts.amazonaws.com`. Skip this if the account
   already has one.
1. Create an IAM role, for example `github-liferay-log-backup`, with this trust policy. It allows only the `main`
   branch of your repository to use the role:

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
          "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
          "StringLike":   { "token.actions.githubusercontent.com:sub": "repo:<ORG>/<REPO>:ref:refs/heads/main" }
        }
      }]
    }
    ```

1. Attach this permissions policy. It allows uploads to the log prefix only: the role can't read, list or delete
   anything.

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::<BUCKET>/liferay-cloud/*"
      }]
    }
    ```

1. Copy the role ARN. In GitHub, go to **Settings → Secrets and variables → Actions** and save it as the secret
   `AWS_ROLE_ARN`.

## Check

In IAM, the role's **Trust relationships** tab shows the GitHub provider and your repository's `main` branch, its
only permission is `s3:PutObject` on `arn:aws:s3:::<BUCKET>/liferay-cloud/*`, and the repository lists the
`AWS_ROLE_ARN` secret.
