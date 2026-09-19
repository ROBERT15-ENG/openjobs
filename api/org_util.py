"""Employer organization / team access helpers."""

from timeutil import utcnow_iso


def get_user_organization_id(db, user_id):
    row = db.execute('SELECT organization_id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not row:
        return None
    return row['organization_id']


def create_organization_for_employer(db, company_name, owner_user_id):
    now = utcnow_iso()
    db.execute(
        'INSERT INTO organizations (name, created_at) VALUES (?, ?)',
        (company_name, now),
    )
    org_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.execute('UPDATE users SET organization_id = ? WHERE id = ?', (org_id, owner_user_id))
    db.execute(
        'INSERT INTO organization_members (organization_id, user_id, role, created_at) VALUES (?, ?, ?, ?)',
        (org_id, owner_user_id, 'owner', now),
    )
    return org_id


def employer_can_access_job(db, user_id, user_role, job_row):
    if user_role == 'admin':
        return True
    if not job_row:
        return False
    employer_id = job_row.get('employer_id')
    if employer_id == user_id:
        return True
    org_id = get_user_organization_id(db, user_id)
    if not org_id or not employer_id:
        return False
    owner = db.execute('SELECT organization_id FROM users WHERE id = ?', (employer_id,)).fetchone()
    return owner and owner['organization_id'] == org_id


def get_employer_job_ids(db, user_id):
    org_id = get_user_organization_id(db, user_id)
    if org_id:
        rows = db.execute(
            """
            SELECT j.id FROM jobs j
            JOIN users u ON j.employer_id = u.id
            WHERE j.employer_id = ? OR u.organization_id = ?
            """,
            (user_id, org_id),
        ).fetchall()
    else:
        rows = db.execute('SELECT id FROM jobs WHERE employer_id = ?', (user_id,)).fetchall()
    return [row['id'] for row in rows]


def get_team_member_user_ids(db, user_id):
    org_id = get_user_organization_id(db, user_id)
    if not org_id:
        return [user_id]
    rows = db.execute(
        'SELECT user_id FROM organization_members WHERE organization_id = ?',
        (org_id,),
    ).fetchall()
    return [row['user_id'] for row in rows] or [user_id]
