---
title: 3. Liferay Cloud にサインインする
parent: 章
nav_order: 3
---

# 3. Liferay Cloud にサインインする
{: .no_toc }

1. TOC
{:toc}

## 目的

キーボードの前に誰もいなくても、ワークフローがサインインできる Liferay Cloud アカウントを用意します。

## ブラウザーを使わずに CLI でサインインする仕組み

Liferay Cloud CLI（`lcp`）には、トークンを渡す環境変数がありません。`lcp login --no-browser` を実行したとき、標準入力がターミナルでなければ（GitHub Actions では常にそうです）、標準入力からメールアドレスとパスワードを半角スペース 1 つで区切って読み込みます。

```bash
printf '%s %s' "$LCP_USER" "$LCP_PASSWORD" | lcp login --no-browser
```

[5 章](workflow.html)のワークフローは、*Authenticate LCP CLI* ステップでこれを行います。

## 手順

1. 対象の環境を参照できる ** 専用の Liferay Cloud サービスユーザー ** を作成するか、選びます。個人のアカウントは避けてください。
1. そのユーザーに **Liferay Cloud のパスワード ** があることを確認します。SSO で作成したアカウントには、設定するまでパスワードがありません。CLI がパスワードの再設定用リンクを表示します。
1. パスワードに ** スペースが含まれていない ** ことを確認します。CLI は入力をスペースで区切るため、途中で切れてしまいます。ワークフローはこれを確認し、分かりやすいエラーで停止します。
1. GitHub の **Settings → Secrets and variables → Actions** で、メールアドレスを `LCP_USER`、パスワードを `LCP_PASSWORD` として保存します。リポジトリには絶対にコミットしないでください。

{: .important }
サービスユーザーのパスワードを変更またはローテーションしたら、同時に `LCP_PASSWORD` も更新してください。更新しないと、すべての実行がサインインのステップで失敗します。

{: .note }
サインイン済みの CLI は、アクセストークンとリフレッシュトークンを `~/.lcp` に保存します。このファイルをシークレットにコピーしても最初は動きますが、更新されたトークンは使い捨てのランナーにしか保存されないため、シークレットはすぐに古くなります。毎回パスワードでサインインすれば、この問題は起きません。

## 確認

Linux または macOS のマシンで、CLI がなければインストールし、ワークフローと同じ方法でサービスユーザーとしてサインインします。

```bash
curl -fsSL https://cdn.liferay.cloud/lcp/stable/latest/install.sh | bash
printf '%s %s' 'service-user@example.com' 'the-password' | lcp login --no-browser
lcp list -p <PROJECT_ID> < /dev/null
lcp logout
```

`lcp list` に `webserver` を含む環境のサービスが表示されれば完了です。
