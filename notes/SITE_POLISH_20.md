# Site polish checklist (20 items)

Shared assets: `static/site-polish.css`, `static/site-polish.js`, `templates/includes/site_polish.html`, `templates/includes/head_polish.html`, `templates/includes/faq.html`.

| # | Feature | Status |
|---|---------|--------|
| 1 | Dark mode toggle | `data-theme` light/dark, FAB ◐ |
| 2 | Cookie banner | Existing `site.js` |
| 3 | Site search | Ctrl+K overlay, pages + `/api/jobs` |
| 4 | Back to top | FAB ↑ after 400px scroll |
| 5 | Mobile menus | Home hamburger (existing) |
| 6 | Loading animations | Job list skeletons |
| 7 | Hover states | Existing CSS |
| 8 | Scroll progress | `#oj-scroll-progress` bar |
| 9 | Copy button | `[data-copy]` + job share |
| 10 | Print stylesheet | `@media print` in site-polish.css |
| 11 | Sticky headers | Existing |
| 12 | Skip to content | All public templates |
| 13 | Password visibility | Login, register, employer auth |
| 14 | UTM tracking | `oj_utm` cookie on strip + form capture |
| 15–16 | Form success/error | Alerts + inline field errors (login) |
| 17 | Confirmation modals | `OpenJobsConfirm` (employer deletes) |
| 18 | Last updated | Job detail listed date |
| 19 | Expandable FAQ | Home `#faq` |
| 20 | Floating contact | FAB mailto `CONTACT_EMAIL` |
