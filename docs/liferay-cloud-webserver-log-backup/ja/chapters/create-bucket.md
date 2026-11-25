---
title: 1. S3 バケットを作成する
parent: 章
nav_order: 1
---

# 1. S3 バケットを作成する
{: .no_toc }

1. TOC
{:toc}

## 目的

非公開で暗号化された S3 バケットを作成し、ライフサイクルルールで、時間の経過とともにログを安価なストレージへ移動し、保持期間が終わったら削除するようにします。

## 手順

1. バケットを作成し、パブリックアクセスをすべてブロックして、デフォルトの暗号化を有効にします。

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

1. 次の内容を `lifecycle.json` として保存し、日数を保持ポリシーに合わせます。この例では、ファイルを 30 日間 Standard ストレージに置いた後、低頻度アクセス（Infrequent Access）へ、90 日後に Glacier へ移動し、400 日（約 13 か月）後に削除します。

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

1. 適用します。

    ```bash
    aws s3api put-bucket-lifecycle-configuration --bucket <BUCKET> \
      --lifecycle-configuration file://lifecycle.json
    ```

{: .tip }
Glacier のファイルは、読めるようになるまでの復元に数分から数時間かかります。90 日より前のインシデントを調査することが多い場合は、Glacier への移動を遅らせるか、Glacier Instant Retrieval（`GLACIER_IR`）を使ってください。

## 確認

```bash
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-lifecycle-configuration --bucket <BUCKET>
```

パブリックアクセスの 4 つの設定がすべて `true`、暗号化ルールが `AES256`、ライフサイクルルールが `Enabled` になっていれば完了です。
