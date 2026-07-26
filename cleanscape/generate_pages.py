#!/usr/bin/env python3
"""Generate SEO service landing pages for Cleanscape Solutions."""

from pathlib import Path

BASE = "https://cleanscapesolutions.com.au"
PHONE = "(08) 9000 1234"
PHONE_TEL = "+61890001234"

SERVICES = [
    {
        "slug": "commercial-cleaning-perth",
        "title": "Commercial Cleaning Perth | Professional Cleaners WA — Cleanscape",
        "description": "Top-rated commercial cleaning in Perth, WA. Offices, retail, warehouses & strata. Locally owned, fully insured. Free quotes — call (08) 9000 1234.",
        "h1": "Commercial Cleaning Perth",
        "subtitle": "Professional commercial cleaners for Perth businesses — offices, retail, warehouses and more across WA.",
        "service_name": "Commercial Cleaning Perth",
        "related": [
            ("office-cleaning-perth.html", "Office Cleaning Perth"),
            ("industrial-cleaning-perth.html", "Industrial Cleaning Perth"),
            ("strata-cleaning-perth.html", "Strata Cleaning Perth"),
        ],
        "sections": [
            ("Why Perth businesses choose Cleanscape", [
                "Cleanscape Solutions is one of Perth's most trusted commercial cleaning companies. We service hundreds of businesses across the Perth metropolitan area — from CBD high-rises and suburban office parks to retail centres in Joondalup, Rockingham, and Fremantle.",
                "As a locally owned Perth cleaning business, we offer faster response times, transparent pricing, and dedicated account managers who understand Western Australian workplaces. Every client receives a free site assessment and a customised cleaning plan.",
            ]),
            ("Our commercial cleaning services in Perth include", [
                "Daily and weekly office cleaning across Perth CBD and suburbs",
                "Retail showroom and shopping centre cleaning",
                "Warehouse, factory, and industrial facility cleaning",
                "Strata common-area and building lobby maintenance",
                "Medical centre and healthcare facility sanitisation",
                "School and childcare centre cleaning with WWCC staff",
                "After-hours, weekend, and 24/7 emergency cleaning",
            ]),
            ("Areas we service across Perth and WA", [
                "We provide commercial cleaning throughout Perth CBD, Subiaco, West Perth, East Perth, Northbridge, Fremantle, Joondalup, Rockingham, Mandurah, Midland, Malaga, Osborne Park, Belmont, Canning Vale, Kwinana, Wangara, Cockburn, and regional Western Australia.",
            ]),
        ],
        "faq": [
            ("How much does commercial cleaning cost in Perth?", "Commercial cleaning in Perth typically ranges from $30–$60 per hour depending on facility size, frequency, and scope. Cleanscape provides free on-site quotes tailored to your Perth property."),
            ("Do you provide commercial cleaning across all Perth suburbs?", "Yes. We service the entire Perth metropolitan area and regional WA. Contact us to confirm availability in your suburb."),
            ("Are your commercial cleaners insured?", "Yes. All staff are police checked and we carry full public liability and workers compensation insurance."),
        ],
    },
    {
        "slug": "office-cleaning-perth",
        "title": "Office Cleaning Perth | Daily & Weekly Office Cleaners — Cleanscape",
        "description": "Professional office cleaning in Perth, WA. Daily, weekly & custom schedules for CBD & suburban offices. Police-checked, insured cleaners. Free quote.",
        "h1": "Office Cleaning Perth",
        "subtitle": "Keep your Perth office spotless with reliable daily, weekly, or custom cleaning schedules.",
        "service_name": "Office Cleaning Perth",
        "related": [
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
            ("strata-cleaning-perth.html", "Strata Cleaning Perth"),
            ("end-of-lease-cleaning-perth.html", "End of Lease Cleaning"),
        ],
        "sections": [
            ("Professional office cleaners for Perth workplaces", [
                "A clean office boosts productivity, impresses clients, and keeps your team healthy. Cleanscape Solutions provides professional office cleaning across Perth — from single-room suites in Subiaco to multi-floor buildings in Perth CBD.",
                "Our Perth office cleaning teams handle workstations, meeting rooms, kitchens, restrooms, reception areas, and common spaces. We work around your business hours with early morning, after-hours, and weekend options available.",
            ]),
            ("What's included in our Perth office cleaning", [
                "Desk and workstation sanitisation",
                "Meeting room and boardroom cleaning",
                "Kitchen and break room cleaning",
                "Restroom cleaning and restocking",
                "Floor vacuuming, mopping, and carpet care",
                "Window and glass partition cleaning",
                "Bin emptying and waste management",
                "High-touch point disinfection",
            ]),
            ("Office cleaning suburbs we cover", [
                "Perth CBD, West Perth, East Perth, Subiaco, Nedlands, Claremont, Osborne Park, Malaga, Belmont, Canning Vale, Joondalup, Midland, and all Perth metro suburbs.",
            ]),
        ],
        "faq": [
            ("How often should offices in Perth be cleaned?", "Most Perth offices benefit from daily or 3x weekly cleaning. We assess your foot traffic, team size, and budget to recommend the ideal schedule."),
            ("Can you clean our office after business hours?", "Yes. After-hours and early morning office cleaning is available across Perth to avoid disrupting your team."),
            ("Do you supply cleaning products?", "Yes. We bring all equipment and eco-friendly products. Custom product requests are welcome."),
        ],
    },
    {
        "slug": "industrial-cleaning-perth",
        "title": "Industrial Cleaning Perth | Warehouse & Factory Cleaners WA",
        "description": "Industrial & warehouse cleaning in Perth, WA. Factories, distribution centres, mining sites. Heavy-duty equipment, insured teams. Free quotes.",
        "h1": "Industrial & Warehouse Cleaning Perth",
        "subtitle": "Heavy-duty industrial cleaning for Perth factories, warehouses, and distribution centres.",
        "service_name": "Industrial Cleaning Perth",
        "related": [
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
            ("builders-clean-perth.html", "Builders Clean Perth"),
            ("office-cleaning-perth.html", "Office Cleaning Perth"),
        ],
        "sections": [
            ("Industrial cleaning experts in Perth, WA", [
                "Perth's industrial sector demands specialised cleaning. Cleanscape Solutions provides heavy-duty warehouse, factory, and distribution centre cleaning across the Perth metro area and regional WA — including Welshpool, Kwinana, Malaga, and Wangara industrial estates.",
                "Our industrial cleaning teams are trained for high-ceiling dust removal, concrete floor scrubbing, machinery degreasing, loading dock cleaning, and compliance with WA workplace health and safety standards.",
            ]),
            ("Industrial cleaning services we provide", [
                "Warehouse and distribution centre cleaning",
                "Factory floor scrubbing and degreasing",
                "High-bay and racking dust removal",
                "Loading dock and yard cleaning",
                "Equipment and machinery cleaning",
                "Construction site and builders clean support",
                "Mining and resources facility cleaning",
                "Scheduled maintenance and one-off deep cleans",
            ]),
            ("Perth industrial zones we service", [
                "Welshpool, Kwinana, Malaga, Wangara, Osborne Park, Bibra Lake, Canning Vale, Midland, Henderson, and regional WA industrial areas.",
            ]),
        ],
        "faq": [
            ("What industrial facilities do you clean in Perth?", "We clean warehouses, factories, distribution centres, workshops, transport hubs, power stations, and mining support facilities across Perth and WA."),
            ("Do you have heavy-duty cleaning equipment?", "Yes. We use industrial floor scrubbers, pressure washers, high-reach equipment, and specialised degreasing products."),
            ("Can you work around our production schedule?", "Absolutely. We offer night shifts, weekend cleaning, and shutdown-period deep cleans."),
        ],
    },
    {
        "slug": "strata-cleaning-perth",
        "title": "Strata Cleaning Perth | Building & Common Area Cleaners WA",
        "description": "Strata cleaning in Perth, WA. Lobbies, lifts, gardens, pools & common areas. Trusted by Perth strata managers. Free quotes — (08) 9000 1234.",
        "h1": "Strata Cleaning Perth",
        "subtitle": "Common-area cleaning for Perth strata buildings — lobbies, lifts, gardens, and pool surrounds.",
        "service_name": "Strata Cleaning Perth",
        "related": [
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
            ("office-cleaning-perth.html", "Office Cleaning Perth"),
            ("residential-cleaning-perth.html", "Residential Cleaning Perth"),
        ],
        "sections": [
            ("Strata cleaning for Perth buildings", [
                "Cleanscape Solutions provides comprehensive strata cleaning for commercial and residential buildings across Perth. We work with strata managers, body corporates, and property managers to maintain lobbies, lifts, stairwells, car parks, gardens, and pool areas to the highest standard.",
                "Our Perth strata cleaning teams understand the expectations of residents and tenants. We provide consistent, reliable service with detailed reporting and flexible scheduling.",
            ]),
            ("Strata cleaning services in Perth include", [
                "Lobby and entrance cleaning",
                "Lift and stairwell maintenance",
                "Car park sweeping and pressure washing",
                "Garden and landscaping tidying",
                "Pool area and BBQ facility cleaning",
                "Bin room and waste area cleaning",
                "Window and glass cleaning",
                "Periodic deep cleans and annual maintenance",
            ]),
            ("Perth strata buildings we service", [
                "Apartment towers in Perth CBD, South Perth, and Scarborough. Mixed-use developments in Subiaco and Leederville. Commercial strata in Osborne Park and Belmont. And residential complexes across all Perth metro suburbs.",
            ]),
        ],
        "faq": [
            ("How often should strata common areas be cleaned?", "Most Perth strata buildings require daily or 3x weekly lobby cleaning, with weekly garden and car park maintenance. We tailor schedules to your building's needs."),
            ("Do you work with strata managers?", "Yes. We partner with strata managers across Perth and provide detailed service reports."),
            ("Can you handle both commercial and residential strata?", "Yes. We clean all types of strata properties across Perth and WA."),
        ],
    },
    {
        "slug": "end-of-lease-cleaning-perth",
        "title": "End of Lease Cleaning Perth | Bond Back Cleaning — Cleanscape",
        "description": "End of lease cleaning in Perth with bond-back guarantee. Kitchens, bathrooms, carpets & full property detail. Book your Perth vacate clean today.",
        "h1": "End of Lease Cleaning Perth",
        "subtitle": "Bond-back guarantee vacate cleaning for renters and property managers across Perth, WA.",
        "service_name": "End of Lease Cleaning Perth",
        "related": [
            ("residential-cleaning-perth.html", "Residential Cleaning Perth"),
            ("builders-clean-perth.html", "Builders Clean Perth"),
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
        ],
        "sections": [
            ("Bond-back end of lease cleaning in Perth", [
                "Moving out of your Perth rental? Cleanscape Solutions provides thorough end of lease cleaning that meets real estate agent and property manager standards. Our vacate cleaning covers every room, surface, and fixture to maximise your bond return.",
                "We clean hundreds of Perth rental properties every year across all suburbs — from studio apartments in Perth CBD to family homes in Joondalup, Rockingham, and Mandurah.",
            ]),
            ("Our Perth end of lease cleaning checklist", [
                "Full kitchen clean — oven, stovetop, rangehood, cupboards inside and out",
                "Bathroom deep clean — tiles, grout, shower screens, toilets, vanities",
                "All rooms — walls, skirting boards, light switches, door frames",
                "Carpet steam cleaning (available as add-on)",
                "Window cleaning — inside and accessible outside",
                "Garage and outdoor area cleaning",
                "Cobweb removal and dusting throughout",
                "Final inspection-ready finish",
            ]),
            ("Perth suburbs for end of lease cleaning", [
                "All Perth metro suburbs including Perth CBD, Subiaco, Fremantle, Joondalup, Rockingham, Mandurah, Midland, Canning Vale, Cockburn, and surrounding areas.",
            ]),
        ],
        "faq": [
            ("How much does end of lease cleaning cost in Perth?", "End of lease cleaning in Perth typically starts from $250 for a 1-bedroom apartment and scales with property size. We provide fixed-price quotes after assessing your property."),
            ("Do you guarantee bond back?", "We clean to real estate inspection standards. If your agent identifies any issues within 72 hours, we return to rectify them at no extra charge."),
            ("How far in advance should I book?", "We recommend booking 1–2 weeks ahead, especially at end-of-month. Emergency bookings are often available."),
        ],
    },
    {
        "slug": "residential-cleaning-perth",
        "title": "Residential Cleaning Perth | House Cleaning Services WA",
        "description": "House cleaning in Perth, WA. Weekly, fortnightly & one-off home cleans. Police-checked cleaners, eco-friendly products. Book your Perth home clean.",
        "h1": "Residential House Cleaning Perth",
        "subtitle": "Regular and one-off house cleaning for Perth homes — weekly, fortnightly, or deep cleans.",
        "service_name": "Residential Cleaning Perth",
        "related": [
            ("end-of-lease-cleaning-perth.html", "End of Lease Cleaning Perth"),
            ("builders-clean-perth.html", "Builders Clean Perth"),
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
        ],
        "sections": [
            ("House cleaning services for Perth homes", [
                "Cleanscape Solutions brings the same professional standards from our commercial work to Perth homes. Whether you need a weekly tidy-up, fortnightly deep clean, or one-off spring clean, our residential cleaning teams deliver consistent, trustworthy service.",
                "All our Perth house cleaners are police checked, fully insured, and trained to respect your home and belongings. We use eco-friendly products safe for children and pets.",
            ]),
            ("Residential cleaning services in Perth", [
                "Regular weekly and fortnightly house cleaning",
                "One-off deep cleans and spring cleaning",
                "Kitchen and bathroom sanitisation",
                "Dusting, vacuuming, and mopping",
                "Bed making and linen changing",
                "Fridge and oven cleaning",
                "Post-renovation residential cleaning",
                "Seniors and NDIS home cleaning support",
            ]),
            ("Perth suburbs we clean", [
                "We provide house cleaning across all Perth metro suburbs — Perth CBD, Subiaco, Nedlands, Cottesloe, Fremantle, Joondalup, Rockingham, Mandurah, Midland, and everywhere in between.",
            ]),
        ],
        "faq": [
            ("How much does house cleaning cost in Perth?", "Regular house cleaning in Perth typically ranges from $35–$55 per hour or $120–$250 for a standard 3-bedroom home. We provide fixed quotes based on your home size and requirements."),
            ("Do I need to be home during the clean?", "No. Many Perth clients provide access and return to a spotless home. We are fully insured for your peace of mind."),
            ("Can I book a one-off clean?", "Yes. One-off deep cleans, spring cleans, and pre-event cleaning are available across Perth."),
        ],
    },
    {
        "slug": "builders-clean-perth",
        "title": "Builders Clean Perth | Post-Construction Cleaning WA",
        "description": "Builders clean & post-construction cleaning in Perth, WA. Dust removal, window cleaning, final handover cleans. For builders, developers & homeowners.",
        "h1": "Builders Clean Perth",
        "subtitle": "Post-construction and renovation cleaning for Perth builders, developers, and homeowners.",
        "service_name": "Builders Clean Perth",
        "related": [
            ("industrial-cleaning-perth.html", "Industrial Cleaning Perth"),
            ("end-of-lease-cleaning-perth.html", "End of Lease Cleaning Perth"),
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
        ],
        "sections": [
            ("Post-construction cleaning in Perth, WA", [
                "Construction and renovation projects leave behind dust, debris, and residue that standard cleaning can't handle. Cleanscape Solutions provides professional builders cleans across Perth — from new home handovers in the northern suburbs to commercial fit-outs in Perth CBD.",
                "We work with Perth builders, developers, project managers, and homeowners to deliver inspection-ready properties. Our teams understand construction timelines and can mobilise quickly for final handover deadlines.",
            ]),
            ("Builders clean services in Perth", [
                "Rough clean during construction phases",
                "Final handover and presentation clean",
                "Construction dust removal from all surfaces",
                "Window and glass cleaning — internal and external",
                "Floor scrubbing — tiles, concrete, and timber",
                "Kitchen and bathroom fixture cleaning",
                "Garage and outdoor area cleanup",
                "Commercial fit-out and tenancy handover cleans",
            ]),
            ("Who we work with in Perth", [
                "Residential builders, commercial developers, renovation contractors, property developers, and homeowners completing renovations across the Perth metropolitan area.",
            ]),
        ],
        "faq": [
            ("What is a builders clean?", "A builders clean removes construction dust, debris, paint splatter, and adhesive residue from a newly built or renovated property, preparing it for handover or occupancy."),
            ("When should I book a builders clean?", "Book your final builders clean 2–3 days before handover or inspection. We can also provide progressive cleans during construction."),
            ("Do you clean commercial construction sites?", "Yes. We provide builders cleans for commercial fit-outs, office renovations, and retail builds across Perth."),
        ],
    },
    {
        "slug": "medical-cleaning-perth",
        "title": "Medical Centre Cleaning Perth | Healthcare Facility Cleaners WA",
        "description": "Medical centre & clinic cleaning in Perth, WA. Hospital-grade sanitisation, infection control, compliance-ready. Trusted healthcare cleaners.",
        "h1": "Medical Centre Cleaning Perth",
        "subtitle": "Healthcare-grade cleaning and sanitisation for Perth medical centres, clinics, and dental practices.",
        "service_name": "Medical Centre Cleaning Perth",
        "related": [
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
            ("school-cleaning-perth.html", "School Cleaning Perth"),
            ("office-cleaning-perth.html", "Office Cleaning Perth"),
        ],
        "sections": [
            ("Healthcare cleaning specialists in Perth", [
                "Medical facilities require a higher standard of cleaning than any other environment. Cleanscape Solutions provides specialised medical centre cleaning across Perth using hospital-grade anti-bacterial products and infection control protocols.",
                "Our Perth healthcare cleaning teams are trained in medical facility standards, understand privacy requirements, and work discreetly around patient schedules. We service GP clinics, dental practices, specialist rooms, allied health centres, and aged care facilities.",
            ]),
            ("Medical cleaning services in Perth include", [
                "Treatment room and surgery sanitisation",
                "Waiting room and reception cleaning",
                "Dental chair and equipment area cleaning",
                "Restroom and patient facility hygiene",
                "High-touch surface disinfection",
                "Biohazard waste area maintenance",
                "Floor care with healthcare-grade products",
                "Compliance documentation and audit support",
            ]),
            ("Perth healthcare facilities we service", [
                "Medical centres across Perth CBD, Subiaco, Nedlands, Joondalup, Rockingham, Midland, and suburban clinic precincts throughout WA.",
            ]),
        ],
        "faq": [
            ("What products do you use for medical cleaning?", "We use TGA-listed hospital-grade disinfectants and anti-bacterial products approved for healthcare environments."),
            ("Are your medical cleaners trained?", "Yes. Our healthcare cleaning staff receive specialised training in infection control and medical facility protocols."),
            ("Can you clean after hours at our clinic?", "Yes. We offer after-hours medical centre cleaning across Perth to avoid disrupting patients."),
        ],
    },
    {
        "slug": "school-cleaning-perth",
        "title": "School Cleaning Perth | Education Facility Cleaners WA",
        "description": "School cleaning in Perth, WA. Classrooms, restrooms & playgrounds. WWCC-verified staff. Trusted by Perth schools & childcare centres.",
        "h1": "School Cleaning Perth",
        "subtitle": "Safe, hygienic cleaning for Perth schools, childcare centres, and education facilities.",
        "service_name": "School Cleaning Perth",
        "related": [
            ("commercial-cleaning-perth.html", "Commercial Cleaning Perth"),
            ("medical-cleaning-perth.html", "Medical Centre Cleaning"),
            ("strata-cleaning-perth.html", "Strata Cleaning Perth"),
        ],
        "sections": [
            ("School cleaning for Perth education facilities", [
                "Clean schools mean healthier students and better learning outcomes. Cleanscape Solutions provides professional school cleaning across Perth — from primary schools in the northern suburbs to high schools in the southern corridors and childcare centres throughout the metro area.",
                "All staff working in Perth schools and childcare facilities hold current Working With Children Checks and national police clearances. We understand term schedules, school holidays, and the need for minimal disruption.",
            ]),
            ("School cleaning services in Perth", [
                "Classroom cleaning and sanitisation",
                "Restroom and changeroom hygiene",
                "Playground and outdoor area maintenance",
                "Staff room and admin office cleaning",
                "Gymnasium and hall cleaning",
                "Canteen and kitchen area cleaning",
                "Window and blind cleaning",
                "Holiday period deep cleans",
            ]),
            ("Perth schools and centres we service", [
                "Primary schools, high schools, private colleges, childcare centres, and early learning facilities across all Perth metro suburbs and regional WA.",
            ]),
        ],
        "faq": [
            ("Do your school cleaners have WWCC?", "Yes. Every staff member working in Perth schools and childcare centres holds a current Working With Children Check."),
            ("When do you clean schools?", "We typically clean after school hours and during holidays for deep cleans. Schedules are tailored to each school's needs."),
            ("Can you clean during school holidays?", "Yes. Holiday period deep cleans are popular for Perth schools — book early as slots fill quickly."),
        ],
    },
]


def render_sections(sections):
    html = ""
    for heading, items in sections:
        if isinstance(items, str):
            items = [items]
        use_list = len(items) > 1 and all(len(i) < 90 for i in items)
        if use_list:
            body = "<ul>\n" + "\n".join(f"            <li>{item}</li>" for item in items) + "\n          </ul>"
        else:
            body = "\n".join(f"          <p>{item}</p>" for item in items)
        html += f"          <h2>{heading}</h2>\n{body}\n"
    return html


def render_page(s: dict) -> str:
    url = f"{BASE}/{s['slug']}.html"
    related_html = "\n".join(
        f'          <li><a href="{href}">{label}</a></li>' for href, label in s["related"]
    )
    sections_html = render_sections(s["sections"])

    faq_html = "\n".join(
        f"""        <details class="faq-item">
          <summary>{q}</summary>
          <p>{a}</p>
        </details>"""
        for q, a in s["faq"]
    )

    faq_schema = ",\n".join(
        f"""          {{
            "@type": "Question",
            "name": "{q}",
            "acceptedAnswer": {{ "@type": "Answer", "text": "{a}" }}
          }}"""
        for q, a in s["faq"]
    )

    return f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{s['title']}</title>
  <meta name="description" content="{s['description']}">
  <meta name="robots" content="index, follow">
  <meta name="geo.region" content="AU-WA">
  <meta name="geo.placename" content="Perth">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="en-au" href="{url}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{url}">
  <meta property="og:title" content="{s['h1']} | Cleanscape Solutions Perth">
  <meta property="og:description" content="{s['description']}">
  <meta property="og:locale" content="en_AU">
  <meta property="og:site_name" content="Cleanscape Solutions">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/style.css">
  <link rel="icon" href="images/favicon.svg" type="image/svg+xml">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{BASE}/" }},
          {{ "@type": "ListItem", "position": 2, "name": "Services", "item": "{BASE}/commercial-cleaning-perth.html" }},
          {{ "@type": "ListItem", "position": 3, "name": "{s['h1']}", "item": "{url}" }}
        ]
      }},
      {{
        "@type": "Service",
        "name": "{s['service_name']}",
        "description": "{s['description']}",
        "provider": {{ "@type": "LocalBusiness", "name": "Cleanscape Solutions", "telephone": "{PHONE_TEL}", "url": "{BASE}/" }},
        "areaServed": {{ "@type": "City", "name": "Perth", "containedInPlace": {{ "@type": "State", "name": "Western Australia" }} }},
        "url": "{url}"
      }},
      {{
        "@type": "FAQPage",
        "mainEntity": [
{faq_schema}
        ]
      }}
    ]
  }}
  </script>
</head>
<body>
  <a href="#main" class="skip-link">Skip to main content</a>

  <header class="site-header" id="top">
    <div class="container header-inner">
      <a href="index.html" class="logo" aria-label="Cleanscape Solutions home">
        <img src="images/logo-icon.svg" alt="Cleanscape Solutions Perth cleaning business" class="logo-img" width="48" height="43">
        <span class="logo-text">
          <strong>Cleanscape</strong>
          <span>Solutions</span>
          <span class="logo-tagline">Cleanliness, Simplified</span>
        </span>
      </a>
      <button class="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav">
        <span></span><span></span><span></span>
      </button>
      <nav class="site-nav" id="site-nav">
        <ul>
          <li><a href="commercial-cleaning-perth.html">Services</a></li>
          <li><a href="index.html#why-perth">Why Us</a></li>
          <li><a href="index.html#about">About</a></li>
          <li><a href="index.html#faq">FAQ</a></li>
          <li><a href="index.html#contact" class="btn btn-nav">Get a Quote</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <main id="main">
    <nav class="breadcrumb container" aria-label="Breadcrumb">
      <a href="index.html">Home</a> <span aria-hidden="true">›</span>
      <a href="commercial-cleaning-perth.html">Services</a> <span aria-hidden="true">›</span>
      <span aria-current="page">{s['h1']}</span>
    </nav>

    <section class="page-hero">
      <div class="container">
        <p class="hero-eyebrow">Perth, Western Australia</p>
        <h1>{s['h1']}</h1>
        <p class="page-hero-lead">{s['subtitle']}</p>
        <a href="index.html#contact" class="btn btn-primary">Get a Free Quote</a>
      </div>
    </section>

    <section class="section">
      <div class="container page-layout">
        <article class="prose">
{sections_html}
        </article>
        <aside class="page-sidebar">
          <div class="sidebar-card">
            <h3>Get a Free Quote</h3>
            <p>Call our Perth team or request a quote online.</p>
            <p><a href="tel:{PHONE_TEL}" class="sidebar-phone">{PHONE}</a></p>
            <a href="index.html#contact" class="btn btn-primary btn-full">Request Quote</a>
          </div>
          <div class="sidebar-card">
            <h3>Related Services</h3>
            <ul class="sidebar-links">
{related_html}
            </ul>
          </div>
          <div class="sidebar-card sidebar-trust">
            <ul>
              <li>✓ Perth local business</li>
              <li>✓ Fully insured</li>
              <li>✓ Police checked staff</li>
              <li>✓ Free on-site quotes</li>
            </ul>
          </div>
        </aside>
      </div>
    </section>

    <section class="section section-alt">
      <div class="container">
        <h2 class="faq-heading">{s['h1']} — FAQ</h2>
        <div class="faq-list">
{faq_html}
        </div>
      </div>
    </section>

    <section class="section cta-banner">
      <div class="container cta-banner-inner">
        <h2>Ready for professional {s['service_name'].lower()}?</h2>
        <p>Contact Cleanscape Solutions — Perth's trusted cleaning business.</p>
        <a href="index.html#contact" class="btn btn-primary">Get Your Free Quote</a>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container footer-grid">
      <div class="footer-brand">
        <div class="footer-logo-wrap">
          <a href="index.html" class="logo">
            <img src="images/logo.svg" alt="Cleanscape Solutions" class="logo-img logo-img--full" width="180" height="158">
          </a>
        </div>
        <p>Perth's local cleaning business for commercial, residential and industrial facilities across WA.</p>
      </div>
      <div class="footer-links">
        <h4>Cleaning Services</h4>
        <ul>
          <li><a href="commercial-cleaning-perth.html">Commercial Cleaning</a></li>
          <li><a href="office-cleaning-perth.html">Office Cleaning</a></li>
          <li><a href="industrial-cleaning-perth.html">Industrial Cleaning</a></li>
          <li><a href="end-of-lease-cleaning-perth.html">End of Lease Cleaning</a></li>
          <li><a href="residential-cleaning-perth.html">Residential Cleaning</a></li>
          <li><a href="builders-clean-perth.html">Builders Clean</a></li>
        </ul>
      </div>
      <div class="footer-links">
        <h4>More Services</h4>
        <ul>
          <li><a href="strata-cleaning-perth.html">Strata Cleaning</a></li>
          <li><a href="medical-cleaning-perth.html">Medical Cleaning</a></li>
          <li><a href="school-cleaning-perth.html">School Cleaning</a></li>
          <li><a href="index.html#areas">Service Areas</a></li>
          <li><a href="index.html#contact">Get a Quote</a></li>
        </ul>
      </div>
      <div class="footer-contact">
        <h4>Contact</h4>
        <p><a href="tel:{PHONE_TEL}">{PHONE}</a></p>
        <p><a href="mailto:info@cleanscapesolutions.com.au">info@cleanscapesolutions.com.au</a></p>
        <p>Perth, WA 6000</p>
      </div>
    </div>
    <div class="container footer-bottom">
      <p>&copy; 2026 Cleanscape Solutions — Cleaning Business Perth WA</p>
    </div>
  </footer>

  <script src="js/main.js" defer></script>
</body>
</html>
"""


def main():
    out = Path(__file__).parent
    for s in SERVICES:
        path = out / f"{s['slug']}.html"
        path.write_text(render_page(s), encoding="utf-8")
        print(f"Wrote {path.name}")


if __name__ == "__main__":
    main()
