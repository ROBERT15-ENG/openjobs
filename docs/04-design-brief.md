# OpenJobs — Design brief

**Brand:** OpenJobs — AI-powered career platform (Australia-focused)  
**Last updated:** October 2026

---

## 1. Brand personality

- **Professional** but approachable — job search is stressful; UI should feel calm and capable.  
- **Tech-forward** — subtle AI cues (gradients, “matching” language), not gimmicky robots.  
- **Trustworthy** — clear legal links, contact details, error states, no dark patterns.

## 2. Visual identity

### Color (CSS tokens — use consistently)

| Token | Hex | Usage |
|-------|-----|--------|
| Background | `#09090f` | Page bg |
| Surface / card | `#111119` – `#18181f` | Cards, modals |
| Border | `#2a2a3e` | Dividers, inputs |
| Text primary | `#ededf0` | Body |
| Text muted | `#6b6b80` | Secondary copy |
| **Primary (brand)** | `#00d4aa` | CTAs, links, focus rings |
| Primary hover | `#00ff88` / `#00a88a` | Hover states |
| Accent | `#c084fc` | Highlights (sparingly) |
| Success | `#22c55e` | Confirmations |
| Error | `#ef4444` | Form errors, alerts |
| Warning | `#f59e0b` | Warnings |

### Typography

- **UI font:** [Inter](https://fonts.google.com/specimen/Inter) — weights 400–800  
- **Monospace (optional):** JetBrains Mono — code or IDs  
- **Scale:** Major third on home (`--type-display` through `--type-caption`); elsewhere ~16px body, 0.8–0.875rem labels

### Logo

- Wordmark: **Open** (white) + **Jobs** (primary green)  
- Subline: “AI-Powered Career Platform”  
- Favicon: dark rounded square + green “OJ” mark (`/static/favicon.svg`)

## 3. Layout principles

- **Max content width:** ~1100–1400px for dashboards; centered columns on marketing.  
- **Sticky header** on marketing and job pages (blur backdrop).  
- **Cards** for job listings: title, company, meta row (location, salary, type), footer actions.  
- **Spacing:** generous padding on mobile (16–24px); touch targets ≥ 44px where possible.

## 4. Components (reuse patterns)

| Component | Spec |
|-----------|------|
| Primary button | Green fill, black text, 10–12px radius, hover lift + glow |
| Ghost button | Transparent, border `var(--border)` |
| Input | Dark bg, border focus → primary + glow ring |
| Job card | Hover border primary; featured badge optional |
| Modal | Job quick-view; skeleton loading state |
| Alerts | `.alert-error` / `.alert-success` tinted borders |
| Cookie banner | Bottom sheet, max-width 520px, two buttons |
| Mobile CTA bar | Fixed bottom on ≤768px — single primary link |

## 5. Motion

- Respect **`prefers-reduced-motion: reduce`** (home implements).  
- Micro-interactions: 0.2s transitions on buttons/cards; avoid long parallax.

## 6. Iconography

- Inline **SVG sprite** on home (`<use href="#ico-*">`)  
- No emoji in production UI except legacy strings — prefer SVG for consistency.

## 7. Imagery & social

- **OG image:** `/static/og-image.svg` — dark gradient, wordmark, tagline  
- Photography: optional; if used, diverse Australian workplaces, not stock-heavy corporate clichés.

## 8. Accessibility

- Skip link to `#main-content` on home  
- Form labels visible; errors announced via visible alert blocks  
- Sufficient contrast on primary green on black (check WCAG for small text)  
- `aria-label` on icon-only buttons (e.g. hamburger)

## 9. Voice & copy

- **Headlines:** direct (“Find Your Next Dream Job”)  
- **CTAs:** action verbs — “Sign Up Free”, “Apply Now”, “Search Jobs”  
- **Errors:** plain language + next step (“Check your connection”)  
- **Legal:** link “Privacy” and “Terms” in footer and cookie banner

## 10. Do / don’t

| Do | Don’t |
|----|--------|
| Use design tokens (`var(--color-primary)`) | Hardcode one-off hex in new pages |
| Keep one primary CTA per screen section | Multiple competing green buttons |
| Show loading skeletons for async lists | Blank white flash |
| Link to real contact email/address in footer | Placeholder “example.com” in production |

## 11. Page-specific notes

| Page | Design focus |
|------|----------------|
| Home | Hero gradient headline; search above fold; chat FAB bottom-right |
| Job | Two-column desktop (detail + sticky apply card); stack on mobile |
| Employer | Dense data tables + kanban; sidebar nav on desktop |
| Login/register | Split layout: story left, form right (desktop) |
| Legal | Simple readable prose, max-width 720px |
