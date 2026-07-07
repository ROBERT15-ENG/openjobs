#!/usr/bin/env python3
"""
JobSeek Telegram Bot
Commands: /search, /remote, /visa, /top, /help
"""
import requests
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

API_BASE = os.environ.get("JOBSEEK_API", "http://localhost:5700")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *JobSeek Bot*\n\n"
        "Commands:\n"
        "/search [query] - Search jobs\n"
        "/remote - Remote jobs only\n"
        "/visa - Visa sponsorship jobs\n"
        "/top - Top rated jobs\n"
        "/help - Help",
        parse_mode="Markdown"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""
    try:
        resp = requests.get(f"{API_BASE}/api/jobs", params={"q": query, "limit": 5}, timeout=10)
        jobs = resp.json()
        
        if not jobs:
            await update.message.reply_text("No jobs found 🔍")
            return
        
        msg = "*Search Results:*\n\n"
        for j in jobs[:5]:
            title = j.get("title", "N/A")
            company = j.get("company", "N/A")
            location = j.get("location", "N/A")
            salary = j.get("salary", "N/A")
            score = j.get("ai_score", 0)
            msg += f"*{title}*\n🏢 {company}\n📍 {location}\n💰 {salary}\n⭐ {score}%\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def remote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get(f"{API_BASE}/api/jobs", params={"remote": "1", "limit": 5}, timeout=10)
        jobs = resp.json()
        
        if not jobs:
            await update.message.reply_text("No remote jobs found 🏠")
            return
        
        msg = "*Remote Jobs:*\n\n"
        for j in jobs[:5]:
            title = j.get("title", "N/A")
            company = j.get("company", "N/A")
            salary = j.get("salary", "N/A")
            msg += f"*{title}*\n🏢 {company}\n💰 {salary}\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def visa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get(f"{API_BASE}/api/jobs", params={"visa": "1", "limit": 5}, timeout=10)
        jobs = resp.json()
        
        if not jobs:
            await update.message.reply_text("No visa sponsorship jobs found 🌍")
            return
        
        msg = "*Visa Sponsorship Jobs:*\n\n"
        for j in jobs[:5]:
            title = j.get("title", "N/A")
            company = j.get("company", "N/A")
            location = j.get("location", "N/A")
            msg += f"*{title}*\n🏢 {company}\n📍 {location}\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get(f"{API_BASE}/api/jobs", params={"min_score": 80, "limit": 5}, timeout=10)
        jobs = resp.json()
        
        if not jobs:
            await update.message.reply_text("No top jobs found ⭐")
            return
        
        msg = "*Top Rated Jobs:*\n\n"
        for j in jobs[:5]:
            title = j.get("title", "N/A")
            company = j.get("company", "N/A")
            score = j.get("ai_score", 0)
            msg += f"*{title}*\n🏢 {company}\n⭐ {score}%\n\n"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    from bot_config import BOT_TOKEN as TELEGRAM_BOT_TOKEN
    
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