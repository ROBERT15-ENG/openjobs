"""SEO helpers: slugs and structured data."""

import json
import re


def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return slug[:max_len].rstrip('-') or 'job'


def job_url_path(job_id: int, title: str) -> str:
    return f'/jobs/{job_id}/{slugify(title)}'


def job_posting_json_ld(job: dict, base_url: str) -> str:
    salary_min = job.get('salary_min')
    salary_max = job.get('salary_max')
    currency = job.get('salary_currency') or 'AUD'
    payload = {
        '@context': 'https://schema.org',
        '@type': 'JobPosting',
        'title': job.get('title'),
        'description': (job.get('description') or '')[:5000],
        'datePosted': job.get('created_at') or job.get('posted_at'),
        'hiringOrganization': {
            '@type': 'Organization',
            'name': job.get('company'),
        },
        'jobLocation': {
            '@type': 'Place',
            'address': {
                '@type': 'PostalAddress',
                'addressLocality': job.get('location') or 'Remote',
            },
        },
        'employmentType': job.get('work_type') or 'FULL_TIME',
        'url': f"{base_url.rstrip('/')}{job_url_path(job['id'], job.get('title', ''))}",
    }
    if salary_min or salary_max:
        payload['baseSalary'] = {
            '@type': 'MonetaryAmount',
            'currency': currency,
            'value': {
                '@type': 'QuantitativeValue',
                'minValue': salary_min,
                'maxValue': salary_max or salary_min,
                'unitText': 'YEAR',
            },
        }
    if job.get('work_arrangement') == 'remote' or 'remote' in (job.get('location') or '').lower():
        payload['jobLocationType'] = 'TELECOMMUTE'
    return json.dumps(payload, ensure_ascii=False)
