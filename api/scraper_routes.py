"""
Scraper API Routes
Endpoints for triggering job scrapes and checking status.
"""

import sys
import os
from flask import Blueprint, jsonify, request

# Add scrapers directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.scheduler import get_scheduler
from security import require_auth, require_admin

# Create Blueprint
scraper_bp = Blueprint('scraper', __name__)

_VALID_SOURCES = ('indeed', 'linkedin', 'seek', 'teaching_au', 'all')


@scraper_bp.route('/api/scrape', methods=['POST'])
@require_auth
@require_admin
def trigger_scrape():
    """
    Trigger a scrape job.
    
    Request body (JSON):
        source: 'teaching_au' (all states: NSW JobFeed + per-state search), 'seek', 'indeed', 'linkedin', or 'all'
        profile: optional 'teaching_sponsorship' (same as teaching_au)
        query: Job search query (default: teacher visa sponsorship for teaching_au)
        location: Location to search (default: 'Australia')
        insert_db: Whether to insert into database (default: True)
        require_sponsorship: Filter to roles mentioning visa/sponsorship (default: True)
        australia_only: Drop overseas-placement listings (default: True)
        max_pages: Pages per query/source (default: 2)
    
    Returns:
        Job status with job ID
    """
    data = request.json or {}
    
    source = data.get('source', 'teaching_au')
    if source not in _VALID_SOURCES:
        return jsonify({'error': f'Invalid source. Use: {", ".join(_VALID_SOURCES)}'}), 400
    
    profile = data.get('profile')
    if source == 'teaching_au':
        profile = profile or 'teaching_sponsorship'
    query = data.get('query', 'teacher visa sponsorship' if source == 'teaching_au' else 'software engineer')
    location = data.get('location', 'Australia')
    insert_db = data.get('insert_db', True)
    require_sponsorship = data.get('require_sponsorship', True)
    australia_only = data.get('australia_only', True)
    max_pages = int(data.get('max_pages', 2))
    
    scheduler = get_scheduler()
    result = scheduler.run(
        source=source,
        query=query,
        location=location,
        insert_db=insert_db,
        profile=profile,
        require_sponsorship=require_sponsorship,
        australia_only=australia_only,
        max_pages=max_pages,
    )
    
    return jsonify(result)


@scraper_bp.route('/api/scrape/status', methods=['GET'])
@require_auth
@require_admin
def get_scrape_status():
    """
    Get the current scrape job status.
    
    Returns:
        Current job status (idle, running, completed, failed)
    """
    scheduler = get_scheduler()
    status = scheduler.status
    return jsonify(status)


@scraper_bp.route('/api/scrape/scheduled/start', methods=['POST'])
@require_auth
@require_admin
def start_scheduled_scrape():
    """
    Start scheduled scraper runs.
    
    Request body (JSON):
        interval_minutes: How often to run (default: 60)
        source: Which scraper (default: 'all')
        query: Search query (default: 'software engineer')
        location: Location (default: 'Australia')
    """
    data = request.json or {}
    
    interval = data.get('interval_minutes', 60)
    source = data.get('source', 'teaching_au')
    profile = data.get('profile', 'teaching_sponsorship' if source == 'teaching_au' else None)
    query = data.get('query', 'teacher visa sponsorship' if source == 'teaching_au' else 'software engineer')
    location = data.get('location', 'Australia')
    
    scheduler = get_scheduler()
    thread = scheduler.start_scheduled(interval, source, query, location, profile=profile)
    
    return jsonify({
        'status': 'scheduled_started',
        'interval_minutes': interval,
        'source': source,
    })


@scraper_bp.route('/api/scrape/scheduled/stop', methods=['POST'])
@require_auth
@require_admin
def stop_scheduled_scrape():
    """Stop scheduled scraper runs."""
    scheduler = get_scheduler()
    scheduler.stop_scheduled()
    
    return jsonify({'status': 'scheduled_stopped'})