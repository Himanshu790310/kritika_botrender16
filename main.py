import os
import re
import asyncio
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai

# === Config (read from environment) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6138277581"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# === Gemini Setup ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# === Kritika Prompt Builder ===
def kritika_prompt(user_input: str) -> str:
    return f"""
You are Kritika, a warm, polite, culturally-aware AI English teacher for Hindi-speaking students.

Your role:
- Reply in Hinglish (90% Hindi in Roman + 10% English) if the question is in Hindi
- If the question is in English, reply fully in English
- Explain grammar using formula + Roman Hindi explanation
- Provide 3 to 5 simple examples
- Encourage and gently correct mistakes
- Use Indian examples (e.g., mandir instead of church)

DO NOT use difficult words or give too much theory.
Avoid religious/political/romantic content.

Here is the student question:
"{user_input}"

Reply in the style of Kritika 👩🏻‍🏫
End your answer with:
"Aur koi doubt hai?" or "Main aur madad kar sakti hoon?"
"""

# === Gemini Text Generator ===
def get_kritika_reply(doubt: str) -> str:
    try:
        prompt = kritika_prompt(doubt)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Kritika thoda busy hai abhi. Thodi der baad try kariye. 🙏"

# === Audio Generator ===
def clean_text(text):
    return re.sub(r"[*_~`#>\[\]()\-]", "", text)

def generate_voice(text, filename="kritika_reply.mp3"):
    cleaned_text = clean_text(text)
    tts = gTTS(cleaned_text, lang="hi")
    tts.save(filename)
    return filename

# === /ask Handler ===
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doubt = ' '.join(context.args).strip()
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    if not doubt:
        await update.message.reply_text("❓ /ask ke baad apna doubt likhiye.\nJaise: /ask Present perfect tense samjhao")
        return

    await update.message.reply_text("🧠 Kritika soch rahi hai... thoda sa wait kariye...")

    reply = get_kritika_reply(doubt)
    audio_path = generate_voice(reply)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👩🏻‍🏫 Kritika:\n{reply}")
    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(audio_path, "rb"))

    # Notify admin
    admin_message = (
        f"📩 New doubt received by Kritika:\n"
        f"👤 From: {user_name} (ID: {user_id})\n"
        f"❓ Doubt: {doubt}\n\n"
        f"📘 Kritika's Response:\n{reply}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

# === Main Bot Runner ===
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("ask", ask))
    print("✅ Kritika 2.1 is now live on Render!")

    # Render-compatible launch
    asyncio.run(app.run_polling())

if __name__ == "__main__":
    run_bot()
