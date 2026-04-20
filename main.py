import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import google.genai as genai

# Use the latest 2026 3.1 Flash Lite (Free Tier for API)
MODEL_ID = "gemini-3.1-flash-lite-preview" 

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Simplified chat handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # SYSTEM_PROMPT included in every call for "Vega" personality
    prompt = f"System: You are Vega, a warm, playful AI companion. Speak naturally.\nUser: {user_text}\nVega:"
    
    try:
        # This is the actual call to the 3.1 model
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt
        ).text
        await update.message.reply_text(response)
    except Exception as e:
        # If you see "429", you're hitting the free limit!
        await update.message.reply_text("I'm a bit tired, give me a second! (Error: 429)")

def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Vega is waking up...")
    app.run_polling()

if __name__ == "__main__":
    main()
