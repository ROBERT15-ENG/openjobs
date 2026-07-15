#!/usr/bin/env python3
"""
OpenJobs Telegram Bot
Commands: /search, /remote, /visa, /top, /help
"""
import os
import re

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

API_BASE = os.environ.get('JOBSEEK_API', 'http://localhost:5700')


def _fetch_jobs(**params) -> list:
    resp = requests.get(f'{API_BASE}/api/jobs', params={**params, 'limit': 5}, timeout=10)
    data = resp.json()
    if isinstance(data, dict):
        return data.get('jobs') or []
    return []


def _escape_md(text: str) -> str:
    return re.sub(r'([_*`\[])', r'\\\1', str(text or ''))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🔍 *OpenJobs Bot*\n\n'
        'Commands:\n'
        '/search [query] - Search jobs\n'
        '/remote - Remote jobs only\n'
        '/visa - Visa sponsorship jobs\n'
        '/top - Featured / newest jobs\n'
        '/help - Help',
        parse_mode='Markdown',
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args) if context.args else ''
    try:
        jobs = _fetch_jobs(q=query)
        if not jobs:
            await update.message.reply_text('No jobs found 🔍')
            return
        lines = ['*Search Results:*', '']
        for job in jobs[:5]:
            title = _escape_md(job.get('title', 'N/A'))
            company = _escape_md(job.get('company', 'N/A'))
            location = _escape_md(job.get('location', 'N/A'))
            salary = _escape_md(job.get('salary', 'N/A'))
            score = job.get('score') or job.get('ai_score') or 0
            lines.append(f'*{title}*\n🏢 {company}\n📍 {location}\n💰 {salary}\n⭐ {score}%\n')
        await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')
    except Exception as exc:
        await update.message.reply_text(f'Error: {exc}')


async def remote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _fetch_jobs(work_arrangement='remote')
        if not jobs:
            await update.message.reply_text('No remote jobs found 🏠')
            return
        lines = ['*Remote Jobs:*', '']
        for job in jobs[:5]:
            lines.append(f"*{_escape_md(job.get('title', 'N/A'))}*\n🏢 {_escape_md(job.get('company', 'N/A'))}\n")
        await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')
    except Exception as exc:
        await update.message.reply_text(f'Error: {exc}')


async def visa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _fetch_jobs(visa='1')
        if not jobs:
            await update.message.reply_text('No visa sponsorship jobs found 🌍')
            return
        lines = ['*Visa Sponsorship Jobs:*', '']
        for job in jobs[:5]:
            lines.append(
                f"*{_escape_md(job.get('title', 'N/A'))}*\n"
                f"🏢 {_escape_md(job.get('company', 'N/A'))}\n"
                f"📍 {_escape_md(job.get('location', 'N/A'))}\n"
            )
        await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')
    except Exception as exc:
        await update.message.reply_text(f'Error: {exc}')


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _fetch_jobs(sort='featured')
        if not jobs:
            await update.message.reply_text('No jobs found ⭐')
            return
        lines = ['*Featured / New Jobs:*', '']
        for job in jobs[:5]:
            title = _escape_md(job.get('title', 'N/A'))
            company = _escape_md(job.get('company', 'N/A'))
            score = job.get('score') or 0
            lines.append(f'*{title}*\n🏢 {company}\n⭐ {score}%\n')
        await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')
    except Exception as exc:
        await update.message.reply_text(f'Error: {exc}')


def main():
    from bot_config import BOT_TOKEN as TELEGRAM_BOT_TOKEN

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('search', search_cmd))
    app.add_handler(CommandHandler('remote', remote_cmd))
    app.add_handler(CommandHandler('visa', visa_cmd))
    app.add_handler(CommandHandler('top', top_cmd))

    print('🤖 OpenJobs Bot starting...')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
