---
title: 3. ログを収集する
parent: 章
nav_order: 3
---

# 3. ログを収集する
{: .no_toc }

1. TOC
{:toc}

## 目的

UTC の 1 日ごとの Web サーバーログを、分類スクリプトが読めるファイルとして用意します。

## 手順

1. ** 推奨：** [Liferay Cloud の Web サーバーログをバックアップ](../../../liferay-cloud-webserver-log-backup/ja/)チュートリアルを設定します。このバックアップは既定の形式と計測用の形式の両方に対応しており、1 日あたり 24 個の `.log.gz` ファイルを S3 の `…/year=YYYY/month=MM/day=DD/` に保存します。1 日分のファイルをダウンロードします。

    ```bash
    aws s3 cp --recursive \
      s3://<BUCKET>/liferay-cloud/<PROJECT_ID>/webserver/year=2026/month=11/day=24/ logs/2026-11-24/
    ```

1. ** バックアップを使わずに試す場合 ** は、CLI で Liferay Cloud から 1 時間分または 1 日分を直接取得します。`--since` と `--until` の両方を必ず指定してください。指定しないと `lcp log` は終了しません。

    ```bash
    mkdir -p logs/2026-11-24
    lcp log -p <PROJECT_ID> -s webserver --since "2026-11-24 00:00" --until "2026-11-25 00:00" \
      --limit 10000 < /dev/null | gzip > logs/2026-11-24/webserver-2026-11-24.log.gz
    ```

    日時が UTC として解釈されるよう、`TZ=UTC` を付けて実行してください。Liferay Cloud はログを 30 日間保持します。

{: .note }
分類スクリプトはプレーンテキストと `.gz` の両方のファイルを読み込み、各行の `tm=1` より前の部分を無視するため、CLI が付ける接頭辞（時刻とインスタンス）は問題になりません。計測用の形式を有効にする前の、既定の形式の行は読み飛ばされます。

## 確認

```bash
zcat logs/2026-11-24/*.gz | grep -c 'tm=1'
```

件数がゼロより十分に大きく、その日のトラフィックとおおむね一致していれば完了です。
