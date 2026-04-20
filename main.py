import os
import re
import httpx
import urllib.parse
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import google.genai as genai
from google.genai import types
import io

MODEL_ID = "gemini-1.5-flash"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- Detect if user wants an image ---
IMAGE_KEYWORDS = re.compile(
    r"\b(generate|create|make|draw|show|send|give me|produce)\b.{0,30}\b(image|photo|picture|pic|illustration|artwork)\b",
    re.IGNORECASE
)

def wants_image(text: str) -> bool:
    return bool(IMAGE_KEYWORDS.search(text))

# --- Extract clean prompt from Gemini ---
async def get_image_prompt(user_input: str) -> str:
    resp = client.models.generate_content(
        model=MODEL_ID,
        contents=f"Extract a clean, detailed image generation prompt from this request. Reply with ONLY the prompt, no other text.\nRequest: {user_input}"
    )
    return resp.text.strip()

# --- Generate image via Pollinations (free, no key) ---
async def generate_image_pollinations(prompt: str) -> bytes:
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    async with httpx.AsyncClient(timeout=60) as client_http:
        response = await client_http.get(url)
        response.raise_for_status()
        return response.content

# --- Handle text messages ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    if wants_image(user_input):
        await update.message.reply_text("Generating your image... 🎨")
        try:
            prompt = await get_image_prompt(user_input)
            image_bytes = await generate_image_pollinations(prompt)
            await update.message.reply_photo(photo=io.BytesIO(image_bytes))
        except Exception as e:
            await update.message.reply_text(f"Couldn't generate image: {e}")
        return

    full_query = f"System: You are Vega, a playful female AI. Chat naturally.\nUser: {user_input}"
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=full_query)
        await update.message.reply_text(response.text)
    except Exception as e:
        if "429" in str(e):
            await update.message.reply_text("My battery is dead! Check your Google AI Studio quota.")
        else:
            await update.message.reply_text(f"Something went wrong: {e}")

# --- Handle voice notes ---
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Heard you, let me listen...")
    try:
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                types.Part.from_bytes(data=bytes(voice_bytes), mime_type="audio/ogg"),
                "Transcribe this voice message, then reply to it as Vega, a playful female AI."
            ]
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Couldn't process voice note: {e}")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: No Telegram Token found!")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Vega is awake!")
    app.run_polling()

if __name__ == "__main__":
    main()
