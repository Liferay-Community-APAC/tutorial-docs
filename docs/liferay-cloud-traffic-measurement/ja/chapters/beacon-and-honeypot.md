---
title: 2. ビーコンとハニーポットを追加する
parent: 章
nav_order: 2
---

# 2. ビーコンとハニーポットを追加する
{: .no_toc }

1. TOC
{:toc}

## 目的

最も強力な 2 つのシグナルを追加します。1 つは、ページの読み込み時と訪問者の操作時に本物のブラウザーが送るページビーコン、もう 1 つは、`robots.txt` を無視するクライアントだけがたどる隠しリンクです。

## 手順

### ページビーコン

1. Liferay Workspace に、クライアントエクステンション `client-extensions/traffic-beacon/` を作成します（[client-extension.yaml](../../chapters/files/client-extensions/traffic-beacon/client-extension.yaml)、[assets/beacon.js](../../chapters/files/client-extensions/traffic-beacon/assets/beacon.js)）。

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

    ビーコンは、ページの読み込み後に `load`、最初のスクロール、クリック、キー入力、タッチで `int`、5 秒後もページが表示されていれば `vis5`、ブラウザーが自動操作を報告していれば（`navigator.webdriver`）`wd` を送ります。nginx は `/_tm/b` に Liferay を通さずに `204` で応答し、ログに記録します。

1. 他のクライアントエクステンションと同じ方法でビルドしてデプロイします。
1. グローバル JS のクライアントエクステンションは、既定では有効になっていません。各サイトの公開ページで **Traffic Beacon** を有効にしてください。ページセットの設定の **JavaScript Client Extensions** にあります（メニューの表記は DXP のバージョンによって異なります）。

### ハニーポット

1. Liferay の各サイトの `robots.txt` の設定に、次を追加します。

    ```
    User-agent: *
    Disallow: /_tm/
    ```

    このルールがないと、すべてのリンクをたどる行儀のよいクローラーもハニーポットにかかってしまいます。

1. 次の隠しリンクを、フッターのフラグメントやテーマのフッターなど、すべての公開ページに表示される場所に配置します（[ダウンロード](../../chapters/files/honeypot-link.html)）。JavaScript で追加するのではなく、サーバーで生成される HTML に含めてください。

    {% raw %}
    ```html
    <a href="/_tm/hp/" rel="nofollow" tabindex="-1" aria-hidden="true"
       style="position:absolute;left:-10000px;width:1px;height:1px;overflow:hidden">.</a>
    ```
    {% endraw %}

    リンクは画面外にあり、スクリーンリーダーからは隠され、Tab キーでも移動しないため、訪問者がたどることはありません。

## 確認

1. ブラウザーで公開ページを開き、スクロールして数秒待ちます。Web サーバーのログに `uri="/_tm/b?t=load…"`、続いて `t=int` と `t=vis5` が、それぞれ `s="204"` で記録されます。
1. `https://<your-site>/robots.txt` に `Disallow: /_tm/` が含まれています。
1. ページの HTML ソースに `/_tm/hp/` へのリンクが含まれています。
