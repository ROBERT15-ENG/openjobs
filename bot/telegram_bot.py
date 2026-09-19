#!/usr/bin/env python3
"""
JobSeek Telegram Bot
Commands: /search, /remote, /visa, /top, /help
"""
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

API_BASE = os.environ.get("JOBSEEK_API", "http://localhost:5700")


def _fetch_jobs(params: dict) -> list:
    """GET /api/jobs and return a plain list regardless of response envelope."""
    params = {"limit": 5, **params}
    resp = requests.get(f"{API_BASE}/api/jobs", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("jobs", [])


def _format_job(j: dict, with_location=True, with_salary=True) -> str:
    lines = [f"*{j.get('title', 'N/A')}*", f"🏢 {j.get('company', 'N/A')}"]
    if with_location:
        lines.append(f"📍 {j.get('location', 'N/A')}")
    if with_salary and j.get("salary"):
        lines.append(f"💰 {j['salary']}")
    return "\n".join(lines) + "\n"


async def _reply_jobs(update: Update, jobs: list, heading: str, empty_msg: str, **fmt):
    if not jobs:
        await update.message.reply_text(empty_msg)
        return
    msg = f"*{heading}*\n\n" + "\n".join(_format_job(j, **fmt) for j in jobs[:5])
    await update.message.reply_text(msg, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *JobSeek Bot*\n\n"
        "Commands:\n"
        "/search [query] - Search jobs\n"
        "/remote - Remote jobs only\n"
        "/visa - Visa sponsorship jobs\n"
        "/top - Featured jobs\n"
        "/help - Help",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    try:
        jobs = _fetch_jobs({"q": query})
        await _reply_jobs(update, jobs, "Search Results:", "No jobs found 🔍")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def remote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _fetch_jobs({"work_arrangement": "remote"})
        await _reply_jobs(update, jobs, "Remote Jobs:", "No remote jobs found 🏠", with_location=False)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def visa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _fetch_jobs({"q": "visa sponsorship"})
        await _reply_jobs(update, jobs, "Visa Sponsorship Jobs:", "No visa sponsorship jobs found 🌍", with_salary=False)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # /api/jobs already sorts featured jobs first
        jobs = [j for j in _fetch_jobs({"limit": 20}) if j.get("is_featured")] or _fetch_jobs({})
        await _reply_jobs(update, jobs, "Top Jobs:", "No top jobs found ⭐", with_location=False)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def main():
    from bot_config import BOT_TOKEN as TELEGRAM_BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Add it to your environment or .env file.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("remote", remote_cmd))
    app.add_handler(CommandHandler("visa", visa_cmd))
    app.add_handler(CommandHandler("top", top_cmd))

    print("🤖 JobSeek Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
