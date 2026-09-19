"""Telegram bot configuration.

The token is read from the TELEGRAM_BOT_TOKEN environment variable (see .env.example).
Never commit a real token to this file.
"""
import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
