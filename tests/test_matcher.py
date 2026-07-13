import os
import sys

API = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
sys.path.insert(0, API)

from semantic_matcher import keyword_score
from status import is_valid_kanban_stage, is_valid_status, normalize_status


def test_normalize_status_aliases():
    assert normalize_status('pending') == 'applied'
    assert normalize_status('reviewing') == 'screening'
    assert normalize_status('INTERVIEW') == 'interview'


def test_valid_statuses():
    assert is_valid_status('applied')
    assert is_valid_status('withdrawn')
    assert not is_valid_status('bogus')


def test_valid_kanban_stages():
    assert is_valid_kanban_stage('screening')
    assert not is_valid_kanban_stage('withdrawn')


def test_keyword_score_finds_overlap():
    score, matched, _missing = keyword_score('Python,Flask', 'Experienced Python developer with Flask APIs')
    assert score >= 2
    assert 'Python' in matched or 'Flask' in matched


def test_keyword_score_no_overlap():
    score, matched, _missing = keyword_score('Java,Spring', 'Graphic designer with Photoshop')
    assert score == 0
    assert matched == []
