"""Gunicorn configuration (production process model).

Threads rather than many processes: request handlers block on SMTP/Ollama/
SQLite I/O, and SQLite has a single writer, so a few worker processes with a
thread pool each gives the best throughput without lock contention.
"""

import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5700')}"
workers = int(os.environ.get('WEB_CONCURRENCY', min(2, multiprocessing.cpu_count())))
threads = int(os.environ.get('GUNICORN_THREADS', '4'))
worker_class = 'gthread'
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '60'))
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
forwarded_allow_ips = os.environ.get('FORWARDED_ALLOW_IPS', '*')
