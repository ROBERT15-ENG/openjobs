"""Employer team account management."""

import datetime

from auth_utils import require_auth
from db import get_db
from flask import Blueprint, jsonify, request
from org_util import get_user_organization_id

teams_bp = Blueprint('teams', __name__)

TEAM_ROLES = ('owner', 'admin', 'recruiter')


@teams_bp.route('/api/employer/team', methods=['GET'])
@require_auth
def list_team():
    if request.user_role not in ('employer', 'admin'):
        return jsonify({'error': 'Employer access required'}), 403

    db = get_db()
    org_id = get_user_organization_id(db, request.user_id)
    if not org_id:
        user = db.execute(
            'SELECT id, name, email, role, company FROM users WHERE id = ?',
            (request.user_id,),
        ).fetchone()
        return jsonify({
            'organization': None,
            'members': [{'user_id': user['id'], 'name': user['name'], 'email': user['email'], 'role': 'owner'}] if user else [],
        })

    org = db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    members = db.execute(
        """
        SELECT om.role, om.created_at, u.id as user_id, u.name, u.email
        FROM organization_members om
        JOIN users u ON u.id = om.user_id
        WHERE om.organization_id = ?
        ORDER BY om.role = 'owner' DESC, u.name ASC
        """,
        (org_id,),
    ).fetchall()
    return jsonify({
        'organization': dict(org) if org else None,
        'members': [dict(row) for row in members],
    })


@teams_bp.route('/api/employer/team', methods=['POST'])
@require_auth
def add_team_member():
    if request.user_role != 'employer':
        return jsonify({'error': 'Employer access required'}), 403

    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    role = (data.get('role') or 'recruiter').strip().lower()
    if not email:
        return jsonify({'error': 'email is required'}), 400
    if role not in TEAM_ROLES or role == 'owner':
        return jsonify({'error': 'role must be one of: admin, recruiter'}), 400

    db = get_db()
    org_id = get_user_organization_id(db, request.user_id)
    if not org_id:
        return jsonify({'error': 'No organization found for this account'}), 400

    caller = db.execute(
        'SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ?',
        (org_id, request.user_id),
    ).fetchone()
    if not caller or caller['role'] not in ('owner', 'admin'):
        return jsonify({'error': 'Only owners or admins can invite team members'}), 403

    invitee = db.execute(
        "SELECT id, name, email, role, organization_id FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if not invitee:
        return jsonify({'error': 'User must register as an employer first, then you can add them'}), 404
    if invitee['role'] != 'employer':
        return jsonify({'error': 'User is not an employer account'}), 400
    if invitee['organization_id'] and invitee['organization_id'] != org_id:
        return jsonify({'error': 'User already belongs to another organization'}), 409

    existing = db.execute(
        'SELECT 1 FROM organization_members WHERE organization_id = ? AND user_id = ?',
        (org_id, invitee['id']),
    ).fetchone()
    if existing:
        return jsonify({'error': 'User is already on your team'}), 409

    now = datetime.datetime.now().isoformat()
    db.execute('UPDATE users SET organization_id = ?, company = (SELECT name FROM organizations WHERE id = ?) WHERE id = ?',
               (org_id, org_id, invitee['id']))
    db.execute(
        'INSERT INTO organization_members (organization_id, user_id, role, created_at) VALUES (?, ?, ?, ?)',
        (org_id, invitee['id'], role, now),
    )
    db.commit()
    return jsonify({'success': True, 'message': f'{invitee["name"]} added to your team'}), 201


@teams_bp.route('/api/employer/team/<int:member_user_id>', methods=['DELETE'])
@require_auth
def remove_team_member(member_user_id):
    if request.user_role != 'employer':
        return jsonify({'error': 'Employer access required'}), 403
    if member_user_id == request.user_id:
        return jsonify({'error': 'Cannot remove yourself'}), 400

    db = get_db()
    org_id = get_user_organization_id(db, request.user_id)
    if not org_id:
        return jsonify({'error': 'No organization'}), 400

    caller = db.execute(
        'SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ?',
        (org_id, request.user_id),
    ).fetchone()
    if not caller or caller['role'] not in ('owner', 'admin'):
        return jsonify({'error': 'Not authorized'}), 403

    target = db.execute(
        'SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ?',
        (org_id, member_user_id),
    ).fetchone()
    if not target:
        return jsonify({'error': 'Member not found'}), 404
    if target['role'] == 'owner':
        return jsonify({'error': 'Cannot remove the organization owner'}), 403

    db.execute(
        'DELETE FROM organization_members WHERE organization_id = ? AND user_id = ?',
        (org_id, member_user_id),
    )
    db.execute('UPDATE users SET organization_id = NULL WHERE id = ?', (member_user_id,))
    db.commit()
    return jsonify({'success': True})
