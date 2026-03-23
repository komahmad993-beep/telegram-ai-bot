from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Salom! Men @InspiRocketBot")

from datetime import datetime

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    
    print(f"{user_id}: (@{username}): {user_text}")

    today = datetime.now().date()

    # user yo‘q bo‘lsa
    if user_id not in user_data:
        user_data[user_id] = {
            "date": today,
            "limit": 15
        }

    # yangi kun bo‘lsa reset
    if user_data[user_id]["date"] != today:
        user_data[user_id]["date"] = today
        user_data[user_id]["limit"] = 15

    # limit tugagan bo‘lsa
    if user_data[user_id]["limit"] <= 0:
        await update.message.reply_text(
            "🚫 Kunlik limit tugadi (15 ta).\n💰 Premium olish uchun yozing."
        )
        return

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_text}
            ]
        )

        bot_reply = response.choices[0].message.content

        # kamaytiramiz
        user_data[user_id]["limit"] -= 1

    except Exception as e:
        bot_reply = f"Xatolik: {e}"

    await update.message.reply_text(
        f"{bot_reply}\n\n🧠 Qoldi: {user_data[user_id]['limit']}/15"
    )
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 InspiRocketBot ishga tushdi...")
app.run_polling()
