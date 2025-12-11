import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === تنظیمات محیطی ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_MODEL = os.environ.get("HF_MODEL", "google/flan-t5-small")  # مدل پیش‌فرض برای تست

if not TELEGRAM_TOKEN or not HF_TOKEN:
    raise SystemExit("توکن‌ها تنظیم نشده‌اند. TELEGRAM_TOKEN و HF_TOKEN را ست کن.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

# === توابع کمکی ===
def build_prompt(persona: str, user_message: str) -> str:
    """
    این پرامپت صرفاً برای نقش‌آفرینی (Role-play) است.
    مخاطب می‌داند که در حال صحبت با یک مدل هوش مصنوعی است،
    اما مدل باید پاسخ‌ها را به سبک یک انسان طبیعی و واقعی شبیه‌سازی کند.
    مدل حق ندارد ادعای انسان‌بودن واقعی یا هویت واقعی داشته باشد؛
    فقط باید رفتار، لحن و شخصیتِ تعریف‌شده را بازنمایی کند.
    هیچ درخواست واقعی، اطلاعات حساس یا اقدام عملی از کاربر نخواهد خواست.
    """

    system = (
        "You are engaging in a consensual role-play with the user. "
        "The user fully knows you are an AI model. "
        "Your only task is to simulate natural human-like behavior in conversation, "
        "based on the persona description below. "
        "Never claim to be a real person. Never imply you have a real identity. "
        "Do not ask the user for anything sensitive or actionable. "
        "Respond naturally, like a real human would speak, but within the boundaries of fiction.\n\n"
    )

    persona_block = f"Persona description: {persona}\n\n"
    user_block = f"User message: {user_message}\n\n"
    instruction = "Reply in a natural, human-like style that reflects the persona.\n"

    return system + persona_block + user_block + instruction

def call_hf_inference(prompt: str, max_tokens: int = 200, temperature: float = 0.7):
    """
    تماس به Hugging Face Inference API (text-generation)
    """
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False},
        # "options": {"use_cache": False}  # اختیاری
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # پاسخ مدل معمولاً فرمت لیستی با dict محتواست. ساده‌ترین برداشت:
    if isinstance(data, dict) and data.get("error"):
        raise Exception("HF error: " + data["error"])
    if isinstance(data, list) and len(data) > 0:
        # معمولاً [{'generated_text': '...'}]
        text = data[0].get("generated_text") or data[0].get("text") or str(data[0])
        return text.strip()
    return str(data)

# === هندلرهای تلگرام ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! برای تعریف شخصیت از دستور\n/role <شرح شخصیت>\nاستفاده کن. مثال:\n/role Amir, a witty Persian history professor"
    )

async def role_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("باید بعد از /role شرح شخصیت را بنویسی.")
        return
    persona = " ".join(args)
    # محافظ ساده: اگر به نظر اسمِ یک چهره میاد، اخطار بده
    lower = persona.lower()
    if any(x in lower for x in ["donald", "elon", "musk", "president", "trump", "biden", "putin"]):
        await update.message.reply_text("درخواست برای جعل افراد واقعی پذیرفته نیست. لطفاً شخصیت خیالی تعریف کن.")
        return
    context.user_data["persona"] = persona
    await update.message.reply_text(f"پرسونای ذخیره شد:\n{persona}\nحالا هر پیام بفرست تا پاسخ براساس این شخصیت تولید بشه.")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    persona = context.user_data.get("persona")
    if persona:
        await update.message.reply_text(f"شخصیت جاری: {persona}")
    else:
        await update.message.reply_text("هنوز پرسونایی تنظیم نکردی. با /role شروع کن.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("persona", None)
    await update.message.reply_text("پرسونا حذف شد.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    persona = context.user_data.get("persona")
    if not persona:
        await update.message.reply_text("اول /role را بزن و شخصیت را تعریف کن.")
        return

    # ساخت پرامپت امن
    prompt = build_prompt(persona, text)