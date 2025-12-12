import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
MODEL = os.getenv("MODEL", "deepseek/deepseek-r1")  # مدل پیش‌فرض

if not TELEGRAM_TOKEN or not OPENROUTER_KEY:
    raise SystemExit("TELEGRAM_TOKEN یا OPENROUTER_KEY پیدا نشد.")

def build_prompt(persona, msg):
    return f"""You are an AI doing a safe fictional roleplay.
Persona: {persona}
User: {msg}
Reply naturally in style of the persona, without claiming to be a real human."""

def call_openrouter(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post(url, json=data, headers=headers)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("برای تنظیم شخصیت از /role استفاده کن.")

async def role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("بعد از /role شخصیتت را بنویس.")
    context.user_data["persona"] = " ".join(context.args)
    await update.message.reply_text("شخصیت تنظیم شد ✔")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    persona = context.user_data.get("persona")
    if not persona:
        return await update.message.reply_text("اول /role را بزن.")

    prompt = build_prompt(persona, update.message.text)
    
    try:
        reply = call_openrouter(prompt)
    except Exception as e:
        reply = f"Error: {e}"

    await update.message.reply_text(reply)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("role", role))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("BOT RUNNING...")
    app.run_polling()
