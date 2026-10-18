/**
 * OpenJobs — cookie consent + optional analytics (GA4).
 * Set GA_MEASUREMENT_ID on the server; analytics loads only after consent.
 */
(function () {
  const CONSENT_KEY = "openjobs_cookie_consent";
  const ANALYTICS_KEY = "openjobs_analytics_opt_in";

  function readConsent() {
    try {
      return JSON.parse(localStorage.getItem(CONSENT_KEY) || "null");
    } catch {
      return null;
    }
  }

  function saveConsent(analytics) {
    const payload = {
      analytics: !!analytics,
      ts: new Date().toISOString(),
    };
    localStorage.setItem(CONSENT_KEY, JSON.stringify(payload));
    localStorage.setItem(ANALYTICS_KEY, analytics ? "1" : "0");
    const banner = document.getElementById("oj-cookie-banner");
    if (banner) banner.hidden = true;
    if (analytics) loadAnalytics();
    syncServerPrivacy(analytics);
  }

  function syncServerPrivacy(analytics) {
    const token = localStorage.getItem("token");
    if (!token) return;
    fetch("/api/user/privacy", {
      method: "PATCH",
      headers: {
        Authorization: "Bearer " + token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ analytics_opt_in: !!analytics }),
    }).catch(function () {});
  }

  function loadAnalytics() {
    const id = document.documentElement.getAttribute("data-ga-id");
    if (!id || window.__ojGaLoaded) return;
    window.__ojGaLoaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    function gtag() {
      dataLayer.push(arguments);
    }
    window.gtag = gtag;
    gtag("js", new Date());
    gtag("config", id, { anonymize_ip: true });
  }

  function initBanner() {
    const existing = readConsent();
    const banner = document.getElementById("oj-cookie-banner");
    if (!banner) return;
    if (existing) {
      banner.hidden = true;
      if (existing.analytics) loadAnalytics();
      return;
    }
    banner.hidden = false;
    document.getElementById("oj-cookie-accept")?.addEventListener("click", function () {
      saveConsent(true);
    });
    document.getElementById("oj-cookie-reject")?.addEventListener("click", function () {
      saveConsent(false);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initBanner);
  } else {
    initBanner();
  }
})();
