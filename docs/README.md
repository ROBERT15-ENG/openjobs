# OpenJobs documentation

## Six-document project pack (start here)

| # | Document | Purpose |
|---|----------|---------|
| 1 | [Product requirements](./01-product-requirements.md) | Features by persona, acceptance criteria |
| 2 | [Technical requirements](./02-technical-requirements.md) | Stack, security, integrations, SLOs |
| 3 | [App flow](./03-app-flow.md) | Routes and user journeys page by page |
| 4 | [Design brief](./04-design-brief.md) | Brand, tokens, components, a11y |
| 5 | [Backend schema](./05-backend-schema.md) | Tables, access control, files |
| 6 | [Implementation plan](./06-implementation-plan.md) | Phased build order and release checklist |

## Other references

| Document | Description |
|----------|-------------|
| [OpenJobs_Project_Documentation.pdf](./OpenJobs_Project_Documentation.pdf) | Consolidated overview PDF |
| [../OpenJobs_CodeSchematic.pdf](../OpenJobs_CodeSchematic.pdf) | API and page schematic |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Architecture notes |
| [../notes/ENGINEERING_ROADMAP.md](../notes/ENGINEERING_ROADMAP.md) | P1/P2/P3 checklist |
| [../notes/SECURITY_AUDIT.md](../notes/SECURITY_AUDIT.md) | Security audit |
| [../notes/DATA_PROTECTION.md](../notes/DATA_PROTECTION.md) | Data protection |
| [../notes/SCRAPERS_TEACHING_AU.md](../notes/SCRAPERS_TEACHING_AU.md) | AU teaching scrapers |

## PDF exports

```bash
# Six-document pack (01-06)
python scripts/compile_project_pack_pdf.py

# Shorter project overview
python scripts/generate_project_documentation_pdf.py
```

Outputs:

- `docs/OpenJobs_Project_Pack.pdf` — full six-document compile
- `docs/OpenJobs_Project_Documentation.pdf` — consolidated overview
