---
title: 2. GitHub と AWS を接続する
parent: 章
nav_order: 2
---

# 2. GitHub と AWS を接続する
{: .no_toc }

1. TOC
{:toc}

## 目的

GitHub の OpenID Connect（OIDC）連携で得た有効期間の短い認証情報を使い、ワークフローがバケットにアップロードできるようにします。使うロールは、それ以外の操作が一切できないものにします。アクセスキーはどこにも保存しません。

## 手順

1. **IAM → Identity providers** で、URL `https://token.actions.githubusercontent.com`、対象者（audience）`sts.amazonaws.com` の OpenID Connect プロバイダーを追加します。アカウントにすでにある場合は省略します。
1. IAM ロール（例：`github-liferay-log-backup`）を、次の信頼ポリシーで作成します。このロールを使えるのは、リポジトリの `main` ブランチだけです。

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

1. 次の権限ポリシーをアタッチします。許可するのはログ用のプレフィックスへのアップロードだけで、読み取り、一覧表示、削除はできません。

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

1. ロールの ARN をコピーします。GitHub の **Settings → Secrets and variables → Actions** で、シークレット `AWS_ROLE_ARN` として保存します。

## 確認

IAM でロールの **Trust relationships** タブに GitHub のプロバイダーとリポジトリの `main` ブランチが表示され、権限が `arn:aws:s3:::<BUCKET>/liferay-cloud/*` への `s3:PutObject` だけで、リポジトリにシークレット `AWS_ROLE_ARN` があれば完了です。
