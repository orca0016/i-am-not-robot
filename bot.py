import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === تنظیمات محیطی ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_MODEL = os.environ.get("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")  # مدل امن HF

if not TELEGRAM_TOKEN or not HF_TOKEN:
    raise SystemExit("توکن‌ها تنظیم نشده‌اند. TELEGRAM_TOKEN و HF_TOKEN را ست کن.")

logging.basicConfig(level=logging.INFO)

# === ساخت پرامپت ===
def build_prompt(persona: str, user_message: str) -> str:
    system = (
        "You are engaging in a consensual role-play with the user. "
        "The user knows you are AI. "
        "Simulate human-like behavior naturally, using the persona below. "
        "Never claim to be a real person or ask sensitive info.\n\n"
    )
    persona_block = f"Persona description: {persona}\n\n"
    user_block = f"User message: {user_message}\n\n"
    instruction = "Reply naturally in style of the persona.\n"
    return system + persona_block + user_block + instruction

# === تماس با Router API HF ===
def call_hf_inference(prompt: str, temperature: float = 0.7, max_tokens: int = 300):
    url = "https://router.huggingface.co/api/chat"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "model": HF_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_output_tokens": max_tokens,
        "temperature": temperature
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # پاسخ واقعی از Router API
    if "error" in data:
        raise Exception(data["error"])
    # محتوا معمولاً در messages[0]['content']['text'] یا مشابه آن
    if "generated_text" in data:
        return data["generated_text"]
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"]
    return str(data)

# === هندلرهای تلگرام ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! برای تعریف شخصیت از /role استفاده کن.")

async def role_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("بعد از /role شرح شخصیت را بنویس.")
        return
    persona = " ".join(args)
    lower = persona.lower()
    if any(x in lower for x in ["donald", "elon", "musk", "president", "trump", "biden", "putin"]):
        await update.message.reply_text("شخصیت واقعی قابل قبول نیست. یک شخصیت خیالی تعریف کن.")
        return
    context.user_data["persona"] = persona
    await update.message.reply_text(f"شخصیت ذخیره شد:\n{persona}")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    persona = context.user_data.get("persona")
    if persona:
        await update.message.reply_text(f"شخصیت فعلی: {persona}")
    else:
        await update.message.reply_text("هنوز شخصیت تنظیم نکرده‌ای.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("persona", None)
    await update.message.reply_text("شخصیت حذف شد.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    persona = context.user_data.get("persona")
    if not persona:
        await update.message.reply_text("اول /role را بزن و شخصیت را مشخص کن.")
        return
    prompt = build_prompt(persona, text)
    try:
        response = call_hf_inference(prompt)
    except Exception as e:
        await update.message.reply_text(f"خطا از HF:\n{e}")
        return
    await update.message.reply_text(response)

# === اجرای بات ===
if __name__ == "__main__":
    print("BOT STARTING...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("role", role_cmd))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("BOT IS NOW RUNNING (POLLING)...")
    app.run_polling()
