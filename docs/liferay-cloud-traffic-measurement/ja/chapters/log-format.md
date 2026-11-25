---
title: 1. 計測用のログ形式を有効にする
parent: 章
nav_order: 1
---

# 1. 計測用のログ形式を有効にする
{: .no_toc }

1. TOC
{:toc}

## 目的

Web サーバーがすべてのリクエストについて、分類スクリプトが必要とするリクエストヘッダーを含む key=value 形式のアクセスログ行を書き込むようにし、ビーコンとハニーポットのアドレスには nginx が直接応答するようにします。

## 仕組み

Liferay Cloud の Web サーバーイメージは、メインのアクセスログについて 2 つの環境変数を読み込みます。

- `LCP_WEBSERVER_NGINX_ACCESS_LOG_MODE`：イメージの既定値は `off` で、この場合 ** アクセスログはまったく書き込まれません **。`all` にする必要があります。
- `LCP_WEBSERVER_LOG_FORMAT`：メインのアクセスログの形式を置き換えます。

Web サーバーの `configs/common/conf.d/` フォルダにあるファイルは nginx の `server` ブロック内に読み込まれるため、変数や `location` を定義できます。

このログ形式では `$remote_addr` を `ra` として記録します。Web サーバーはロードバランサーのアドレスを使って `X-Forwarded-For` から実際のクライアントを特定しているため、この値は信頼できます。`X-Forwarded-For` の左端の値はクライアントが自由に書けるため、参考として記録するだけです。

## 手順

1. nginx の設定を、Liferay Cloud のプロジェクトリポジトリの `webserver/configs/common/conf.d/traffic-measurement.conf` として保存します（[ダウンロード](../../chapters/files/webserver/configs/common/conf.d/traffic-measurement.conf)）。

    {% raw %}
    ```nginx
    # webserver/configs/common/conf.d/traffic-measurement.conf
    #
    # Included inside the server block of the Liferay Cloud webserver image.
    # Deploy this file in the same change as, or before, LCP_WEBSERVER_LOG_FORMAT in
    # LCP.json: the log format uses $tm_auth, and nginx refuses to start if the
    # variable is not defined here.

    # Browser claims a signed-in session. Liferay sets LFR_SESSION_STATE_<userId>,
    # but any client can send this cookie, so the classifier only uses it to label
    # page views that already passed the bot checks. It never skips the checks.
    set $tm_auth "";
    if ($http_cookie ~* "LFR_SESSION_STATE_") { set $tm_auth "1"; }

    # Page beacon endpoint. Answered by nginx, never reaches Liferay.
    location = /_tm/b {
        add_header Cache-Control "no-store" always;
        return 204;
    }

    # Honeypot. Add "Disallow: /_tm/" to the site's robots.txt so that only
    # clients that ignore robots.txt request it.
    location = /_tm/hp/ {
        add_header Cache-Control "no-store" always;
        add_header X-Robots-Tag "noindex, nofollow" always;
        return 204;
    }
    ```
    {% endraw %}

1. 次の 2 つの変数を `webserver/LCP.json` の `env` セクションに追加します（[スニペットをダウンロード](../../chapters/files/webserver/LCP.json.snippet)）。

    {% raw %}
    ```json
    {
      "env": {
        "LCP_WEBSERVER_NGINX_ACCESS_LOG_MODE": "all",
        "LCP_WEBSERVER_LOG_FORMAT": "tm=1 ts=\"$time_iso8601\" xff=\"$http_x_forwarded_for\" ra=\"$remote_addr\" host=\"$host\" m=\"$request_method\" uri=\"$request_uri\" s=\"$status\" ct=\"$sent_http_content_type\" b=\"$body_bytes_sent\" rt=\"$request_time\" urt=\"$upstream_response_time\" ua=\"$http_user_agent\" ref=\"$http_referer\" al=\"$http_accept_language\" acc=\"$http_accept\" sfs=\"$http_sec_fetch_site\" sfm=\"$http_sec_fetch_mode\" sfd=\"$http_sec_fetch_dest\" chua=\"$http_sec_ch_ua\" chp=\"$http_sec_ch_ua_platform\" cs=\"$cookie_COOKIE_SUPPORT\" auth=\"$tm_auth\" rid=\"$request_id\""
      }
    }
    ```
    {% endraw %}

1. 2 つのファイルを ** 同じ変更で ** コミットし、まず開発環境、次に UAT、最後に本番環境にデプロイします。

{: .warning }
このログ形式は `$tm_auth` を使いますが、この変数を定義しているのは `.conf` ファイルだけです。ファイルなしで変数だけが反映されると **nginx が起動しなくなり **（`unknown "tm_auth" variable`）、Web サーバーが再起動を繰り返します。`LCP.json` の変更だけを単独でデプロイしないでください。

{: .note }
各行は既定の形式の約 2 倍の長さになります。本番の前に、ログ量とログのバックアップの実行時間への影響を確認してください。

## 確認

デプロイ後、Web サーバーサービスのログにエラーがなく、アクセスログの行が `tm=1` で始まっていれば完了です。

```bash
lcp log -p <PROJECT_ID> -s webserver --since "10 minutes ago" --until "now" | grep -m3 'tm=1'
```

各行に `ts="…+00:00"`、パブリック IP アドレスの `ra="…"`、そして `al="ja,en;q=0.9"` のようなブラウザーのヘッダーが含まれます。
