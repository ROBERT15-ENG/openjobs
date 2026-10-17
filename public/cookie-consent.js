(function () {
  var STORAGE_KEY = "oj_cookie_consent_v1";

  function readConsent() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    } catch (e) {
      return null;
    }
  }

  function saveConsent(prefs) {
    prefs.updated_at = new Date().toISOString();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    hideBanner();
  }

  function hideBanner() {
    var el = document.getElementById("oj-cookie-banner");
    if (el) el.remove();
  }

  function injectStyles() {
    if (document.getElementById("oj-cookie-styles")) return;
    var s = document.createElement("style");
    s.id = "oj-cookie-styles";
    s.textContent =
      "#oj-cookie-banner{position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#111119;border-top:1px solid #2a2a3e;padding:1rem 1.25rem;font-family:Inter,system-ui,sans-serif;box-shadow:0 -8px 32px rgba(0,0,0,.45)}" +
      "#oj-cookie-banner .oj-inner{max-width:960px;margin:0 auto;display:flex;flex-wrap:wrap;gap:1rem;align-items:center;justify-content:space-between}" +
      "#oj-cookie-banner p{margin:0;font-size:.875rem;color:#d4d4dc;flex:1;min-width:220px;line-height:1.5}" +
      "#oj-cookie-banner a{color:#00d4aa}" +
      "#oj-cookie-banner .oj-actions{display:flex;flex-wrap:wrap;gap:.5rem}" +
      "#oj-cookie-banner button{border:none;border-radius:8px;padding:.55rem 1rem;font-size:.8rem;font-weight:600;cursor:pointer}" +
      "#oj-cookie-banner .oj-accept{background:#00d4aa;color:#000}" +
      "#oj-cookie-banner .oj-essential{background:transparent;color:#ededf0;border:1px solid #2a2a3e}" +
      "#oj-cookie-banner .oj-manage{background:transparent;color:#00d4aa;border:1px solid #00d4aa}";
    document.head.appendChild(s);
  }

  function showBanner() {
    injectStyles();
    if (document.getElementById("oj-cookie-banner")) return;
    var div = document.createElement("div");
    div.id = "oj-cookie-banner";
    div.setAttribute("role", "dialog");
    div.setAttribute("aria-label", "Cookie consent");
    div.innerHTML =
      '<div class="oj-inner">' +
      "<p>We use essential cookies and local storage for sign-in and security. " +
      "Optional analytics cookies are off unless you enable them. " +
      '<a href="/cookies">Cookie Policy</a> · <a href="/privacy">Privacy</a></p>' +
      '<div class="oj-actions">' +
      '<button type="button" class="oj-essential" data-action="essential">Essential only</button>' +
      '<button type="button" class="oj-manage" data-action="manage">Manage</button>' +
      '<button type="button" class="oj-accept" data-action="accept-all">Accept all</button>' +
      "</div></div>";
    document.body.appendChild(div);
    div.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-action]");
      if (!btn) return;
      var action = btn.getAttribute("data-action");
      if (action === "essential") {
        saveConsent({ essential: true, analytics: false });
      } else if (action === "accept-all") {
        saveConsent({ essential: true, analytics: true });
      } else if (action === "manage") {
        var analytics = window.confirm(
          "Enable optional analytics cookies? (We do not load third-party analytics unless you agree.)"
        );
        saveConsent({ essential: true, analytics: !!analytics });
      }
    });
  }

  if (!readConsent()) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", showBanner);
    } else {
      showBanner();
    }
  }

  window.OpenJobsCookieConsent = {
    get: readConsent,
    set: saveConsent,
  };
})();
