# Cleanscape Solutions Website

Professional commercial and industrial cleaning company website for **Cleanscape Solutions** — serving Perth and Western Australia.

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
└── README.md
```

## Customisation

Update contact details in `index.html` (phone, email, ABN) and adjust brand colours in `css/style.css` (`:root` variables).

The quote form opens the user's email client via `mailto:` — connect a backend or form service (e.g. Formspree, Netlify Forms) for server-side submission if needed.

## Deployment

Static files only. Deploy to any static host:

- **Netlify / Vercel** — point build output to the `cleanscape` folder
- **GitHub Pages** — set `cleanscape/` as the publishing source
- **Any web server** — upload the `cleanscape` directory contents
