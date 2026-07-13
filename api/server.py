#!/usr/bin/env python3
"""OpenJobs API entry point."""

from app_factory import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5700, debug=False)
