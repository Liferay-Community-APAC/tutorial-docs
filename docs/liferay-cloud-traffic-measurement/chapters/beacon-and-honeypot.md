---
title: 2. Add the Beacon and Honeypot
parent: Chapters
nav_order: 2
---

# 2. Add the Beacon and Honeypot
{: .no_toc }

1. TOC
{:toc}

## Goal

Add the two strongest signals: a page beacon that real browsers send when a page loads and when the visitor
interacts, and a hidden link that only clients ignoring `robots.txt` follow.

## Steps

### The page beacon

1. Create the client extension in your Liferay Workspace as `client-extensions/traffic-beacon/`
   ([client-extension.yaml](files/client-extensions/traffic-beacon/client-extension.yaml),
   [assets/beacon.js](files/client-extensions/traffic-beacon/assets/beacon.js)):

    {% raw %}
    ```yaml
    assemble:
        - from: assets
          into: static

    traffic-beacon:
        name: Traffic Beacon
        type: globalJS
        url: beacon.js
        scriptLocation: bottom
    ```
    {% endraw %}

    {% raw %}
    ```javascript
    // beacon.js
    (function () {
    	var sent = {};
    	var events = ['scroll', 'pointerdown', 'keydown', 'mousemove', 'touchstart'];

    	function send(type) {
    		if (sent[type]) {
    			return;
    		}
    		sent[type] = true;

    		var url = '/_tm/b?t=' + type +
    			'&p=' + encodeURIComponent(location.pathname + location.search) +
    			'&n=' + Math.random().toString(36).slice(2, 10);

    		if (navigator.sendBeacon) {
    			navigator.sendBeacon(url);
    		}
    		else {
    			new Image().src = url;
    		}
    	}

    	function onInteraction() {
    		send('int');
    		events.forEach(function (name) {
    			removeEventListener(name, onInteraction, true);
    		});
    	}

    	send('load');

    	if (navigator.webdriver) {
    		send('wd');
    	}

    	events.forEach(function (name) {
    		addEventListener(name, onInteraction, {capture: true, passive: true});
    	});

    	setTimeout(function () {
    		if (document.visibilityState === 'visible') {
    			send('vis5');
    		}
    	}, 5000);
    })();
    ```
    {% endraw %}

    The beacon sends `load` once the page has loaded, `int` on the first scroll, click, key press or touch, `vis5`
    if the page is still visible after 5 seconds, and `wd` if the browser reports automation
    (`navigator.webdriver`). nginx answers `/_tm/b` with `204` without passing it to Liferay, and logs it.

1. Build and deploy it the way you deploy your other client extensions.
1. Global JS client extensions are not active by default. Enable **Traffic Beacon** for the public pages of each
   site, in the page set's configuration under **JavaScript Client Extensions** (the menu wording varies between
   DXP versions).

### The honeypot

1. In each site's `robots.txt` settings in Liferay, add:

    ```
    User-agent: *
    Disallow: /_tm/
    ```

    Without this rule, the honeypot also catches well-behaved crawlers that follow every link.

1. Put this hidden link in a place that appears on every public page, such as a footer fragment or the theme's
   footer ([download it](files/honeypot-link.html)). It must be in the server-rendered HTML, not added by JavaScript:

    {% raw %}
    ```html
    <a href="/_tm/hp/" rel="nofollow" tabindex="-1" aria-hidden="true"
       style="position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden">.</a>
    ```
    {% endraw %}

    It is off-screen, hidden from screen readers and skipped by the Tab key, so visitors never reach it.

## Check

1. Open a public page in a browser, scroll, and wait a few seconds. The webserver log shows
   `uri="/_tm/b?t=load…"`, then `t=int` and `t=vis5`, each with `s="204"`.
1. `https://<your-site>/robots.txt` contains `Disallow: /_tm/`.
1. The page's HTML source contains the `/_tm/hp/` link.
