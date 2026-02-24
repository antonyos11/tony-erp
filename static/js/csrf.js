// Lightweight global CSRF helper for Django
// - Reads token from a meta tag rendered by the template
// - Adds X-CSRFToken to same-origin unsafe requests (fetch & jQuery)
(function () {
  function getMetaToken() {
    var el = document.querySelector('meta[name="csrf-token"]');
    return el && el.getAttribute('content');
  }
  function getInputToken() {
    var el = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return el && el.value;
  }

  function isMethodSafe(method) {
    var m = String(method || 'GET').toUpperCase();
    return m === 'GET' || m === 'HEAD' || m === 'OPTIONS' || m === 'TRACE';
  }

  function isSameOrigin(url) {
    try {
      var loc = window.location;
      var u = new URL(url, loc.href);
      return u.origin === loc.origin;
    } catch (e) {
      return true; // If URL parsing fails, assume same-origin (relative URLs)
    }
  }

  function ensureHeader(headers, name, value) {
    if (!headers) return;
    try {
      if (headers instanceof Headers) {
        if (!headers.has(name)) headers.set(name, value);
      } else if (Array.isArray(headers)) {
        var has = headers.some(function (h) { return String(h[0]).toLowerCase() === String(name).toLowerCase(); });
        if (!has) headers.push([name, value]);
      } else if (typeof headers === 'object') {
        var keyLower = Object.keys(headers).find(function (k) { return String(k).toLowerCase() === String(name).toLowerCase(); });
        if (!keyLower) headers[name] = value;
      }
    } catch (e) { /* no-op */ }
  }

  var token = getMetaToken() || getInputToken();
  if (token) {
    // Expose for ad-hoc scripts
    window.CSRF_TOKEN = token;

    // Patch fetch
    if (window.fetch) {
      var _fetch = window.fetch;
      window.fetch = function (input, init) {
        try {
          var req = input instanceof Request ? input : null;
          var method = (init && init.method) || (req && req.method) || 'GET';
          var url = (req && req.url) || (typeof input === 'string' ? input : String(input));
          var same = isSameOrigin(url);
          if (same && !isMethodSafe(method)) {
            if (req) {
              var cloneInit = { method: req.method, headers: new Headers(req.headers), body: req.body, mode: req.mode, credentials: req.credentials, cache: req.cache, redirect: req.redirect, referrer: req.referrer, referrerPolicy: req.referrerPolicy, integrity: req.integrity, keepalive: req.keepalive, signal: req.signal }; // minimal copy
              ensureHeader(cloneInit.headers, 'X-CSRFToken', token);
              return _fetch(new Request(req, cloneInit), init);
            } else {
              init = init || {};
              init.headers = init.headers || {};
              ensureHeader(init.headers, 'X-CSRFToken', token);
            }
          }
        } catch (e) { /* fall through */ }
        return _fetch(input, init);
      };
    }

    // jQuery ajaxSetup (if jQuery present)
    if (window.jQuery && jQuery.ajaxSetup) {
      jQuery.ajaxSetup({
        beforeSend: function (xhr, settings) {
          try {
            var same = !settings.crossDomain && isSameOrigin(settings.url || '');
            if (same && !isMethodSafe(settings.type || settings.method)) {
              // Only set if not already set
              if (!settings.headers || !('X-CSRFToken' in settings.headers)) {
                xhr.setRequestHeader('X-CSRFToken', token);
              }
            }
          } catch (e) { /* no-op */ }
        }
      });
    }
  }
})();
