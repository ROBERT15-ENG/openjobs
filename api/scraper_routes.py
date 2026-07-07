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

# Create Blueprint
scraper_bp = Blueprint('scraper', __name__)


@scraper_bp.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """
    Trigger a scrape job.
    
    Request body (JSON):
        source: 'indeed', 'linkedin', or 'all' (default: 'all')
        query: Job search query (default: 'software engineer')
        location: Location to search (default: 'Australia')
        insert_db: Whether to insert into database (default: True)
    
    Returns:
        Job status with job ID
    """
    data = request.json or {}
    
    source = data.get('source', 'all')
    if source not in ('indeed', 'linkedin', 'all'):
        return jsonify({'error': 'Invalid source. Use: indeed, linkedin, or all'}), 400
    
    query = data.get('query', 'software engineer')
    location = data.get('location', 'Australia')
    insert_db = data.get('insert_db', True)
    
    scheduler = get_scheduler()
    result = scheduler.run(source=source, query=query, location=location, insert_db=insert_db)
    
    return jsonify(result)


@scraper_bp.route('/api/scrape/status', methods=['GET'])
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
    source = data.get('source', 'all')
    query = data.get('query', 'software engineer')
    location = data.get('location', 'Australia')
    
    scheduler = get_scheduler()
    thread = scheduler.start_scheduled(interval, source, query, location)
    
    return jsonify({
        'status': 'scheduled_started',
        'interval_minutes': interval,
        'source': source,
    })


@scraper_bp.route('/api/scrape/scheduled/stop', methods=['POST'])
def stop_scheduled_scrape():
    """Stop scheduled scraper runs."""
    scheduler = get_scheduler()
    scheduler.stop_scheduled()
    
    return jsonify({'status': 'scheduled_stopped'})