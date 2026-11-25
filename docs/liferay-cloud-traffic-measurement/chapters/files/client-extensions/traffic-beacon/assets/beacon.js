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
