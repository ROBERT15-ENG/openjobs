"""Register Flask blueprints."""

from blueprints.admin import admin_bp
from blueprints.ai import ai_bp
from blueprints.applications import applications_bp
from blueprints.auth import auth_bp
from blueprints.employer import employer_bp
from blueprints.jobs import jobs_bp
from blueprints.messages import messages_bp
from blueprints.pages import pages_bp
from blueprints.payments import payments_bp
from blueprints.reports import reports_bp
from blueprints.seeker import seeker_bp
from blueprints.teams import teams_bp


def register_blueprints(app):
    for blueprint in (
        auth_bp,
        jobs_bp,
        applications_bp,
        seeker_bp,
        employer_bp,
        admin_bp,
        payments_bp,
        ai_bp,
        messages_bp,
        reports_bp,
        teams_bp,
        pages_bp,
    ):
        app.register_blueprint(blueprint)
