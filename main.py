# main.py
import os
import re
import asyncio
from gtts import gTTS
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import Dispatcher
import google.generativeai as genai
from io import BytesIO

# ENV VARS
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def kritika_prompt(user_input: str) -> str:
    return f"""
You are Kritika, an English teacher for Hindi-speaking students...
Student question: "{user_input}"
"""

def get_kritika_reply(doubt: str) -> str:
    prompt = kritika_prompt(doubt)
    try:
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

# Telegram + FastAPI setup
app = FastAPI()
bot = Bot(BOT_TOKEN)
telegram_app = Application.builder().token(BOT_TOKEN).build()
dispatcher = telegram_app

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = ' '.join(context.args).strip()
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    if not doubt:
        await update.message.reply_text("❓ /ask ke baad apna doubt likhiye.")
        return

    await update.message.reply_text("🧠 Kritika soch rahi hai...")

    reply = get_kritika_reply(doubt)
    voice = generate_voice(reply)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👩🏻‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=voice)

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"👤 {user_name} (ID: {user_id})\n❓ {doubt}\n📘 {reply}")

# Register handler
telegram_app.add_handler(CommandHandler("ask", ask))

@app.post("/")
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(RENDER_EXTERNAL_URL)
    await telegram_app.start()
    print("✅ Kritika is live on webhook.")

