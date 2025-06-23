import os
import re
from gtts import gTTS
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai
from io import BytesIO
import asyncio

# === Environment Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# === Gemini setup ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# === Kritika prompt ===
def kritika_prompt(user_input: str) -> str:
    return f"""
You are Kritika, a kind, clear English teacher for Hindi-speaking students...

Student asked: "{user_input}"

Reply in Hinglish with explanation + 3-5 examples. End with:
"Aur koi doubt hai?" or "Main aur madad kar sakti hoon?"
"""

def get_kritika_reply(doubt: str) -> str:
    try:
        prompt = kritika_prompt(doubt)
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

def clean_text(text):
    return re.sub(r"[*_~`#>\[\]()\-]", "", text)

def generate_voice(text):
    cleaned_text = clean_text(text)
    tts = gTTS(cleaned_text, lang="hi")
    buffer = BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer

# === FastAPI app + Telegram bot ===
app = FastAPI()
bot = Bot(BOT_TOKEN)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# === /ask command handler ===
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = ' '.join(context.args).strip()
    user = update.effective_user

    if not doubt:
        await update.message.reply_text("❓ /ask ke baad apna doubt likhiye.")
        return

    await update.message.reply_text("🧠 Kritika soch rahi hai...")

    reply = get_kritika_reply(doubt)
    voice = generate_voice(reply)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👩🏻‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=voice)

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"👤 {user.full_name} (ID: {user.id})\n❓ {doubt}\n📘 {reply}")

# Register handler
telegram_app.add_handler(CommandHandler("ask", ask))

# === Webhook endpoint ===
@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# === Startup event for Render ===
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(RENDER_EXTERNAL_URL)
    print("✅ Kritika is now live via webhook!")
