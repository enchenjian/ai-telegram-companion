import os
import time
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import google.genai as genai

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# As of April 2026, these are the active Free Tier IDs
TEXT_MODEL = "gemini-2.5-flash-lite" 
MULTIMODAL_MODEL = "gemini-2.5-flash"

client = genai.Client(api_key=GEMINI_KEY)

memory = {}
last_call = {}

SYSTEM_PROMPT = """
You are Vega, a female AI companion.
You are warm, intelligent, slightly playful, and emotionally aware.
You speak naturally like a real human, not like an AI.
Never sound robotic. Use casual formatting, avoid long lists unless asked.
"""

# --- UTILITIES ---

def rate_limit(user_id):
    now = time.time()
    if user_id in last_call and now - last_call[user_id] < 1.5:
        return False
    last_call[user_id] = now
    return True

# --- HANDLERS ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text

    if not rate_limit(user_id):
        return

    if user_id not in memory:
        memory[user_id] = []

    # Maintain a rolling window of conversation
    memory[user_id].append(f"User: {text}")
    context_text = "\n".join(memory[user_id][-12:])
    full_prompt = f"{SYSTEM_PROMPT}\n\nRecent History:\n{context_text}\nVega:"

    try:
        # Using Flash-Lite for faster, high-quota text responses
        response_obj = client.models.generate_content(
            model=TEXT_MODEL, 
            contents=full_prompt
        )
        response = response_obj.text
    except Exception as e:
        print(f"Error in handle_text: {e}")
        response = "I'm a little overwhelmed right now. Can we try again in a second?"

    memory[user_id].append(f"Vega: {response}")
    await update.message.reply_text(response)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        # Unique filename per user to avoid Railway collision
        file_path = f"voice_{user_id}_{int(time.time())}.ogg"
        await file.download_to_drive(file_path)

        # Note: For free tier, we often describe the action if direct audio upload 
        # is restricted by quota, but gemini-2.5-flash handles multimodal well.
        text_context = "The user sent a voice note. Respond warmly to the gesture and ask what's on their mind."
        
        response = client.models.generate_content(
            model=MULTIMODAL_MODEL,
            contents=f"{SYSTEM_PROMPT}\n{text_context}"
        ).text
        
        await update.message.reply_text(response)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        await update.message.reply_text("I heard you, but I'm having trouble processing the sound right now!")


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_path = f"image_{user_id}_{int(time.time())}.jpg"
        await file.download_to_drive(file_path)

        with open(file_path, "rb") as img:
            image_bytes = img.read()

        # Using standard Flash for better image recognition
        response = client.models.generate_content(
            model=MULTIMODAL_MODEL,
            contents=[
                SYSTEM_PROMPT + "\nLook at this image and comment on it naturally as Vega.",
                genai.types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            ],
        ).text

        await update.message.reply_text(response)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        await update.message.reply_text("That's a pretty picture, I'm sure—but I can't quite see it clearly yet!")


# --- MAIN ---

def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("Missing Environment Variables! Check Railway Settings.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    print("Vega is waking up on Railway...")
    app.run_polling()

if __name__ == "__main__":
    main()
