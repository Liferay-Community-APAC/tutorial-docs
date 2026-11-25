---
title: 6. テストして本番運用を始める
parent: 章
nav_order: 6
---

# 6. テストして本番運用を始める
{: .no_toc }

1. TOC
{:toc}

## 目的

ワークフローを手動で 1 回実行し、ファイルが欠けていないことを確認してから、本番開始前のチェックリストを確認します。

## 手順

1. GitHub で **Actions → Backup Liferay Cloud webserver logs → Run workflow** を開きます。
1. 24 個の時間ジョブがすべて成功したことを確認します。各ジョブのログは `Uploaded N lines ...` で終わり、その前の行に、残した行の最初と最後のタイムスタンプが表示されます。
1. S3 に 24 個のファイルがあることを確認します。

    ```bash
    aws s3 ls s3://<BUCKET>/liferay-cloud/<PROJECT_ID>/webserver/year=YYYY/month=MM/day=DD/
    ```

    このコマンドには、ご自身の AWS ユーザーに読み取り権限が必要です。ワークフローのロールはアップロードしかできません。

1. ファイルを 1 つダウンロードし、最初と最後の行が想定した UTC の 1 時間（HH:00〜HH:59）に入っていることを確認します。

    ```bash
    aws s3 cp s3://<BUCKET>/liferay-cloud/<PROJECT_ID>/webserver/year=YYYY/month=MM/day=DD/webserver-<PROJECT_ID>-YYYY-MM-DDT13.log.gz .
    zcat webserver-*-T13.log.gz | head -1
    zcat webserver-*-T13.log.gz | tail -1
    ```

1. ** 欠けがないか確認する:** アクセスの多い時間について、その時間のファイルの行数（`zcat … | wc -l`）を、Liferay Cloud コンソールに表示される同じ時間の件数と比べます。
1. ** 実行時間を確認する:** 最も遅い *Back up hour* ステップと、実行全体にかかった時間を記録し、[大量のログ](operate.html#large-volumes)の目安と比べます。

{: .note }
ワークフローがバックアップするのは常に前日分だけです。本番開始より前の、まだ 30 日以内の日はコピーされません。必要な場合は、期限が切れる前にエクスポートしてください。

## 本番開始前のチェックリスト

- [ ] S3 バケットを作成した：パブリックアクセスをブロック、デフォルトの暗号化を有効化、ライフサイクルルールが保持ポリシーと一致
- [ ] GitHub の OIDC プロバイダーと IAM ロールを作成した。ロールで許可しているのはログ用プレフィックスへの `s3:PutObject` だけ
- [ ] シークレット `AWS_ROLE_ARN`、`LCP_USER`、`LCP_PASSWORD` をリポジトリに保存した
- [ ] サービスユーザーにスペースを含まない Liferay Cloud のパスワードがあり、対象の環境を参照できる
- [ ] 手動のテスト実行が成功し、アクセスの多い時間の行数がコンソールと一致した
- [ ] テストした日の 24 時間分のファイルがすべてある。実行時間を環境のログ量と照らし合わせた
- [ ] `max-parallel` を 4 より大きくする場合は、Liferay Cloud のサポートと合意した
- [ ] 失敗通知が運用チームに届き、チームが **Re-run failed jobs** の使い方を知っている

## 確認

翌朝、01:30 UTC のスケジュール実行が自動で成功し、前日分の 24 個のファイルが S3 にあれば完了です。
