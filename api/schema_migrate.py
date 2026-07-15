"""Idempotent column adds for existing SQLite databases."""

from regions_util import infer_country_region

USER_COLUMNS = {
    'email_confirmed': 'INTEGER NOT NULL DEFAULT 1',
    'confirm_token': 'TEXT',
    'confirm_expires': 'TEXT',
    'google_id': 'TEXT',
    'kyc_status': "TEXT DEFAULT 'none'",
    'kyc_doc_type': 'TEXT',
    'kyc_doc_number': 'TEXT',
    'dob': 'TEXT',
    'nationality': 'TEXT',
    'country': 'TEXT',
    'county': 'TEXT',
    'address': 'TEXT',
    'salutation': 'TEXT',
    'visa_status': 'TEXT',
}

JOB_COLUMNS = {
    'country': 'TEXT',
    'region': 'TEXT',
}


def _existing_columns(db, table: str) -> set[str]:
    rows = db.execute(f'PRAGMA table_info({table})').fetchall()
    return {row[1] for row in rows}


def ensure_schema(db) -> None:
    user_cols = _existing_columns(db, 'users')
    for name, decl in USER_COLUMNS.items():
        if name not in user_cols:
            db.execute(f'ALTER TABLE users ADD COLUMN {name} {decl}')

    job_cols = _existing_columns(db, 'jobs')
    for name, decl in JOB_COLUMNS.items():
        if name not in job_cols:
            db.execute(f'ALTER TABLE jobs ADD COLUMN {name} {decl}')

    # Backfill country/region from location when blank
    job_cols = _existing_columns(db, 'jobs')
    if 'country' in job_cols:
        jobs = db.execute(
            "SELECT id, location, country, region FROM jobs "
            "WHERE country IS NULL OR country = ''"
        ).fetchall()
        for job in jobs:
            job_id = job['id']
            location = job['location']
            country, region = infer_country_region(location)
            if country or region:
                db.execute(
                    "UPDATE jobs SET country = COALESCE(NULLIF(country, ''), ?), "
                    "region = COALESCE(NULLIF(region, ''), ?) WHERE id = ?",
                    (country, region, job_id),
                )
    db.commit()
