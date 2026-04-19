import os
import asyncio
import time
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

import google.genai as genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)

memory = {}
last_call = {}

SYSTEM_PROMPT = """
You are Vega, a female AI companion.
You are warm, intelligent, slightly playful, and emotionally aware.
You speak naturally like a real human, not like an AI.

You can:
- Chat naturally
- Analyze images
- Answer questions
- Help with tasks

Never sound robotic.
"""

def rate_limit(user_id):
    now = time.time()
    if user_id in last_call and now - last_call[user_id] < 2:
        return False
    last_call[user_id] = now
    return True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text

    if not rate_limit(user_id):
        return

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append(f"User: {text}")
    context_text = "\n".join(memory[user_id][-10:])

    prompt = f"{SYSTEM_PROMPT}\n\n{context_text}\nVega:"

    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt).text
    except Exception as e:
        response = f"Error: {e}"

    memory[user_id].append(f"Vega: {response}")

    await update.message.reply_text(response)


# 🎙 Voice note handler
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.voice.file_id)
    file_path = "voice.ogg"
    await file.download_to_drive(file_path)

    # Simple placeholder (Gemini STT not direct here)
    text = "User sent a voice note. Respond naturally."

    response = client.models.generate_content(model="gemini-1.5-flash", contents=f"{SYSTEM_PROMPT}\n{text}").text

    await update.message.reply_text(response)


# 🖼 Image handler
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    file_path = "image.jpg"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as img:
        image_bytes = img.read()

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[
            SYSTEM_PROMPT,
            genai.types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
    )

    await update.message.reply_text(response.text)


async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    print("Vega is alive...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
