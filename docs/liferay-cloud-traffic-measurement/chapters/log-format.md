---
title: 1. Turn On the Measurement Log Format
parent: Chapters
nav_order: 1
---

# 1. Turn On the Measurement Log Format
{: .no_toc }

1. TOC
{:toc}

## Goal

Make the webserver write an access-log line for every request, in a key=value format with the request headers the
classifier needs, and answer the beacon and honeypot addresses directly in nginx.

## How it works

The Liferay Cloud webserver image reads two environment variables for its main access log:

- `LCP_WEBSERVER_NGINX_ACCESS_LOG_MODE`: the image's default is `off`, which writes **no access logs at all**. It
  must be `all`.
- `LCP_WEBSERVER_LOG_FORMAT`: replaces the format of the main access log.

Files in the webserver's `configs/common/conf.d/` folder are included inside nginx's `server` block, so they can
define variables and `location`s.

The format logs `$remote_addr` as `ra`. The webserver already resolves it to the real client from
`X-Forwarded-For`, using the load balancer's address, so it can be trusted. The left end of `X-Forwarded-For` is
written by the client and is only logged for reference.

## Steps

1. Save the nginx config as `webserver/configs/common/conf.d/traffic-measurement.conf` in the Liferay Cloud project
   repository ([download it](files/webserver/configs/common/conf.d/traffic-measurement.conf)):

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

1. Merge these two variables into the `env` section of `webserver/LCP.json`
   ([download the snippet](files/webserver/LCP.json.snippet)):

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

1. Commit both files **in the same change** and deploy to a development environment first, then UAT, then
   production.

{: .warning }
The log format uses `$tm_auth`, which only the `.conf` file defines. If the variables arrive without the file,
**nginx refuses to start** (`unknown "tm_auth" variable`) and the webserver goes into a restart loop. Never deploy the
`LCP.json` change on its own.

{: .note }
Each line is about twice as long as the default format. Check the effect on log volume, and on the log backup's run
time, before production.

## Check

After the deployment, the webserver service's log shows no errors, and its access lines start with `tm=1`:

```bash
lcp log -p <PROJECT_ID> -s webserver --since "10 minutes ago" --until "now" | grep -m3 'tm=1'
```

Each line has `ts="…+00:00"`, `ra="…"` with a public IP address, and the browser headers, for example
`al="ja,en;q=0.9"`.
