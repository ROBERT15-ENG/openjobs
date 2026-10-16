#!/usr/bin/env python3
"""
OpenJobs Telegram Bot — job search via the OpenJobs API / chatbot.
Commands: /search, /remote, /visa, /intern, /help
Free text is handled by /api/chatbot.
"""
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

API_BASE = os.environ.get("JOBSEEK_API", os.environ.get("OPENJOBS_API", "http://localhost:5700"))


def _get_jobs(params: dict) -> list:
    resp = requests.get(f"{API_BASE}/api/jobs", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("jobs") or []


def _chatbot_reply(text: str) -> str:
    resp = requests.post(
        f"{API_BASE}/api/chatbot",
        json={"message": text, "use_ai": False},
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("reply") or "Sorry, I couldn't process that."


def _format_jobs(jobs: list, heading: str) -> str:
    if not jobs:
        return "No jobs found. Try another search on OpenJobs."
    lines = [heading, ""]
    for j in jobs[:5]:
        title = j.get("title", "N/A")
        company = j.get("company", "N/A")
        location = j.get("location", "N/A")
        salary = j.get("salary", "N/A")
        lines.append(f"*{title}*\n🏢 {company}\n📍 {location}\n💰 {salary}\n")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *OpenJobs Bot*\n\n"
        "Search Australian tech and professional roles from OpenJobs.\n\n"
        "Commands:\n"
        "/search [query] — Search jobs\n"
        "/remote — Remote roles\n"
        "/visa — Visa sponsorship\n"
        "/intern — Internships\n"
        "/help — Help\n\n"
        "Or just type what you're looking for in plain English.",
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    try:
        jobs = _get_jobs({"q": query, "limit": 5})
        await update.message.reply_text(
            _format_jobs(jobs, "*Search results:*"),
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def remote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _get_jobs({"remote": "1", "limit": 5})
        await update.message.reply_text(
            _format_jobs(jobs, "*Remote jobs:*"),
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def visa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _get_jobs({"visa": "1", "limit": 5})
        await update.message.reply_text(
            _format_jobs(jobs, "*Visa sponsorship:*"),
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def intern_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jobs = _get_jobs({"work_type": "internship", "limit": 5})
        await update.message.reply_text(
            _format_jobs(jobs, "*Internships:*"),
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    try:
        reply = _chatbot_reply(update.message.text)
        await update.message.reply_text(reply[:4000], parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def main():
    from bot_config import BOT_TOKEN

    if not BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in your environment (see .env.example).")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("remote", remote_cmd))
    app.add_handler(CommandHandler("visa", visa_cmd))
    app.add_handler(CommandHandler("intern", intern_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text))

    print("🤖 OpenJobs Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
