/**
 * OpenJobs site polish: theme, scroll progress, back-to-top, site search,
 * confirm modal, UTM read, FAQ, copy buttons.
 */
(function () {
  const THEME_KEY = "openjobs_theme";
  const UTM_KEY = "openjobs_utm";

  const SITE_PAGES = [
    { title: "Find jobs", href: "/", keywords: "home jobs search" },
    { title: "Sign up", href: "/register", keywords: "register account seeker" },
    { title: "Log in", href: "/login", keywords: "login sign in" },
    { title: "For employers", href: "/employer", keywords: "post job hire" },
    { title: "Privacy policy", href: "/privacy", keywords: "privacy cookies data" },
    { title: "Terms of use", href: "/terms", keywords: "terms legal" },
    { title: "Premium visa roles", href: "/register?plan=visa_premium", keywords: "visa sponsorship premium" },
  ];

  function initTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") {
      document.documentElement.setAttribute("data-theme", stored);
    }
    document.getElementById("oj-theme-toggle")?.addEventListener("click", function () {
      const next =
        document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem(THEME_KEY, next);
      this.setAttribute("aria-label", next === "light" ? "Switch to dark mode" : "Switch to light mode");
      this.textContent = next === "light" ? "☀" : "◐";
    });
    const btn = document.getElementById("oj-theme-toggle");
    if (btn) {
      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      btn.textContent = isLight ? "☀" : "◐";
    }
  }

  function initScrollProgress() {
    const bar = document.getElementById("oj-scroll-progress");
    const topBtn = document.getElementById("oj-back-top");
    if (!bar && !topBtn) return;
    function onScroll() {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      const p = h > 0 ? (window.scrollY / h) * 100 : 0;
      if (bar) bar.style.width = p + "%";
      if (topBtn) topBtn.classList.toggle("visible", window.scrollY > 400);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    topBtn?.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function initSiteSearch() {
    const overlay = document.getElementById("oj-site-search");
    const input = document.getElementById("oj-site-search-input");
    const results = document.getElementById("oj-site-search-results");
    if (!overlay || !input || !results) return;

    function open() {
      overlay.classList.add("open");
      input.value = "";
      renderResults("");
      input.focus();
    }
    function close() {
      overlay.classList.remove("open");
    }

    document.getElementById("oj-site-search-open")?.addEventListener("click", open);
    overlay.querySelector("[data-close]")?.addEventListener("click", close);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });

    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        open();
      }
      if (e.key === "Escape" && overlay.classList.contains("open")) close();
    });

    let jobTimer;
    input.addEventListener("input", function () {
      const q = input.value.trim();
      clearTimeout(jobTimer);
      jobTimer = setTimeout(function () {
        renderResults(q);
      }, 200);
    });

    async function renderResults(q) {
      const ql = q.toLowerCase();
      const pages = SITE_PAGES.filter(function (p) {
        if (!ql) return true;
        return (
          p.title.toLowerCase().includes(ql) ||
          p.keywords.toLowerCase().includes(ql) ||
          p.href.toLowerCase().includes(ql)
        );
      });
      let html = pages
        .map(function (p) {
          return '<a href="' + p.href + '">' + escapeHtml(p.title) + "</a>";
        })
        .join("");

      if (ql.length >= 2) {
        try {
          const res = await fetch("/api/jobs?q=" + encodeURIComponent(q) + "&limit=5");
          const data = await res.json();
          (data.jobs || []).forEach(function (j) {
            html +=
              '<a href="/job?id=' +
              j.id +
              '">Job: ' +
              escapeHtml(j.title) +
              " · " +
              escapeHtml(j.company || "") +
              "</a>";
          });
        } catch (_) {}
      }
      if (!html) html = '<div class="oj-site-search-hint">No matches</div>';
      results.innerHTML = html;
    }

    window.OpenJobsSearch = { open: open, close: close };
  }

  function initConfirmModal() {
    const overlay = document.getElementById("oj-confirm");
    if (!overlay) return;
    const titleEl = document.getElementById("oj-confirm-title");
    const bodyEl = document.getElementById("oj-confirm-body");
    const okBtn = document.getElementById("oj-confirm-ok");
    const cancelBtn = document.getElementById("oj-confirm-cancel");
    let resolver = null;

    function close(result) {
      overlay.classList.remove("open");
      if (resolver) {
        resolver(result);
        resolver = null;
      }
    }

    okBtn?.addEventListener("click", function () {
      close(true);
    });
    cancelBtn?.addEventListener("click", function () {
      close(false);
    });

    window.OpenJobsConfirm = function (opts) {
      opts = opts || {};
      titleEl.textContent = opts.title || "Are you sure?";
      bodyEl.textContent = opts.message || "";
      okBtn.textContent = opts.confirmLabel || "Confirm";
      okBtn.classList.toggle("neutral", !!opts.neutral);
      overlay.classList.add("open");
      return new Promise(function (resolve) {
        resolver = resolve;
      });
    };
  }

  function initCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const sel = btn.getAttribute("data-copy");
        const el = sel ? document.querySelector(sel) : null;
        const text = el ? (el.textContent || "").trim() : btn.getAttribute("data-copy-text") || "";
        if (!text) return;
        navigator.clipboard.writeText(text).then(function () {
          const prev = btn.textContent;
          btn.textContent = "Copied";
          setTimeout(function () {
            btn.textContent = prev;
          }, 1500);
        });
      });
    });
  }

  function readUtmCookie() {
    const m = document.cookie.match(/(?:^|;\s*)oj_utm=([^;]+)/);
    if (!m) return null;
    try {
      return JSON.parse(decodeURIComponent(m[1]));
    } catch {
      return null;
    }
  }

  function initUtmOnForms() {
    const utm = readUtmCookie();
    if (!utm) return;
    document.querySelectorAll("form[data-capture-utm]").forEach(function (form) {
      Object.keys(utm).forEach(function (key) {
        if (!form.querySelector('[name="' + key + '"]')) {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = key;
          input.value = utm[key];
          form.appendChild(input);
        }
      });
    });
    if (window.gtag && utm.utm_source) {
      gtag("event", "campaign_attribution", utm);
    }
  }

  window.OpenJobsFieldError = function (inputId, message) {
    const input = document.getElementById(inputId);
    const msg = document.querySelector('[data-error-for="' + inputId + '"]');
    if (!input) return;
    input.classList.toggle("form-field-error", !!message);
    if (msg) {
      msg.textContent = message || "";
      msg.classList.toggle("show", !!message);
    }
  };

  window.OpenJobsJobsLoading = function (listId) {
    const list = document.getElementById(listId || "jobsList");
    if (!list) return;
    list.innerHTML =
      '<div class="oj-jobs-loading">' +
      '<div class="oj-skeleton-card"></div><div class="oj-skeleton-card"></div><div class="oj-skeleton-card"></div>' +
      "</div>";
  };

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function boot() {
    initTheme();
    initScrollProgress();
    initSiteSearch();
    initConfirmModal();
    initCopyButtons();
    initUtmOnForms();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
