# Cleanscape Solutions Website

Professional commercial and industrial cleaning company website for **Cleanscape Solutions** — serving Perth and Western Australia.

**Live domain:** [https://cleanscapesolutions.com.au/](https://cleanscapesolutions.com.au/)

## Quick Start

Open `index.html` in a browser, or serve locally:

```bash
cd cleanscape
python3 -m http.server 8080
```

Then visit [http://localhost:8080](http://localhost:8080).

## Structure

```
cleanscape/
├── index.html      # Single-page site (hero, services, about, contact)
├── css/style.css   # Styles and responsive layout
├── js/main.js      # Navigation, form handling, scroll animations
├── robots.txt      # Search engine directives
├── sitemap.xml     # Sitemap for cleanscapesolutions.com.au
├── CNAME           # Custom domain (GitHub Pages)
└── README.md
```

## Customisation

Update contact details in `index.html` (phone, email, ABN) and adjust brand colours in `css/style.css` (`:root` variables).

The quote form opens the user's email client via `mailto:` — connect a backend or form service (e.g. Formspree, Netlify Forms) for server-side submission if needed.

## SEO & ranking strategy

This site is built for **top Google rankings** in Perth, WA:

- **10 indexed pages** — homepage + 9 service landing pages, each targeting specific keywords
- **Unique content** per page with Perth suburbs, FAQs, and structured data
- **Internal linking** — every page cross-links to related services
- **Schema markup** — LocalBusiness, Service, FAQPage, BreadcrumbList on every page
- **Sitemap** — submit `https://cleanscapesolutions.com.au/sitemap.xml` to Google Search Console

### Service pages

| Page | Target keyword |
|------|----------------|
| `commercial-cleaning-perth.html` | commercial cleaning Perth |
| `office-cleaning-perth.html` | office cleaning Perth |
| `industrial-cleaning-perth.html` | industrial cleaning Perth |
| `end-of-lease-cleaning-perth.html` | end of lease cleaning Perth |
| `residential-cleaning-perth.html` | house cleaning Perth |
| `strata-cleaning-perth.html` | strata cleaning Perth |
| `builders-clean-perth.html` | builders clean Perth |
| `medical-cleaning-perth.html` | medical centre cleaning Perth |
| `school-cleaning-perth.html` | school cleaning Perth |

Regenerate service pages after editing content: `python3 generate_pages.py`

## SEO

- Optimised title, meta description, and geo tags for Perth/WA local search
- JSON-LD structured data: LocalBusiness, CleaningService, WebSite, FAQPage, reviews, service catalog
- FAQ section and service area content targeting commercial cleaning keywords
- Internal linking with anchor IDs per service (`#office-cleaning`, `#industrial-cleaning`, etc.)
- `robots.txt` and `sitemap.xml` configured for cleanscapesolutions.com.au

After deploying, submit the sitemap in [Google Search Console](https://search.google.com/search-console).

## Deployment to cleanscapesolutions.com.au

Static files only. Upload the contents of the `cleanscape/` folder to your web host's document root.

### GitHub Pages

1. Push the `cleanscape/` folder to your repo
2. In repo Settings → Pages, set source to the `cleanscape` folder (or `/docs` if moved)
3. Add custom domain `cleanscapesolutions.com.au` — the included `CNAME` file handles this
4. At your domain registrar, point DNS:
   - **A records** → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - Or **CNAME** `www` → `your-username.github.io`

### Netlify / Vercel

- Set publish directory to `cleanscape`
- Add custom domain `cleanscapesolutions.com.au` in project settings
- Update DNS per the host's instructions

### GoDaddy / cPanel

Replace the existing site builder files with the contents of `cleanscape/` via File Manager or FTP, pointing the domain to the folder containing `index.html`.
