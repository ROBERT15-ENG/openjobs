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

_VALID_SOURCES = (
    'indeed',
    'linkedin',
    'seek',
    'teaching_au',
    'visa_sponsorship_au',
    'all',
)


@scraper_bp.route('/api/scrape', methods=['POST'])
@require_auth
@require_admin
def trigger_scrape():
    """
    Trigger a scrape job.
    
    Request body (JSON):
        source: 'visa_sponsorship_au' (all occupations + skilled list match), 'teaching_au', 'seek', 'indeed', 'linkedin', or 'all'
        profile: optional 'teaching_sponsorship', 'visa_sponsorship_au'
        query: Job search query (default: teacher visa sponsorship for teaching_au)
        location: Location to search (default: 'Australia')
        insert_db: Whether to insert into database (default: True)
        require_sponsorship: Filter to roles mentioning visa/sponsorship (default: True)
        require_occupation_on_demand: Match data/au_skilled_occupations.json (default: True for visa_sponsorship_au)
        min_occupation_score: Keyword match threshold (default: 3)
        australia_only: Drop overseas-placement listings (default: True)
        max_pages: Pages per query/source (default: 2)
    
    Returns:
        Job status with job ID
    """
    data = request.json or {}
    
    source = data.get('source', 'visa_sponsorship_au')
    if source not in _VALID_SOURCES:
        return jsonify({'error': f'Invalid source. Use: {", ".join(_VALID_SOURCES)}'}), 400
    
    profile = data.get('profile')
    if source == 'teaching_au':
        profile = profile or 'teaching_sponsorship'
    elif source == 'visa_sponsorship_au':
        profile = profile or 'visa_sponsorship_au'
    default_query = 'software engineer'
    if source == 'teaching_au':
        default_query = 'teacher visa sponsorship'
    elif source == 'visa_sponsorship_au':
        default_query = 'visa sponsorship Australia'
    query = data.get('query', default_query)
    location = data.get('location', 'Australia')
    insert_db = data.get('insert_db', True)
    require_sponsorship = data.get('require_sponsorship', True)
    require_occupation_on_demand = data.get(
        'require_occupation_on_demand',
        source == 'visa_sponsorship_au',
    )
    min_occupation_score = int(data.get('min_occupation_score', 3))
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
        require_occupation_on_demand=require_occupation_on_demand,
        min_occupation_score=min_occupation_score,
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
    source = data.get('source', 'visa_sponsorship_au')
    if source == 'teaching_au':
        default_profile = 'teaching_sponsorship'
        default_query = 'teacher visa sponsorship'
    elif source == 'visa_sponsorship_au':
        default_profile = 'visa_sponsorship_au'
        default_query = 'visa sponsorship Australia'
    else:
        default_profile = None
        default_query = 'software engineer'
    profile = data.get('profile', default_profile)
    query = data.get('query', default_query)
    location = data.get('location', 'Australia')
    require_occupation_on_demand = data.get(
        'require_occupation_on_demand',
        source == 'visa_sponsorship_au',
    )
    
    scheduler = get_scheduler()
    thread = scheduler.start_scheduled(
        interval,
        source,
        query,
        location,
        profile=profile,
        require_occupation_on_demand=require_occupation_on_demand,
    )
    
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