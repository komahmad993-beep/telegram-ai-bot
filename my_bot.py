from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_limits = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Salom! Men @InspiRocketBot")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    # limitni tekshiramiz
    if user_id not in user_limits:
        user_limits[user_id] = 5

    if user_limits[user_id] <= 0:
        await update.message.reply_text(
            "🚫 Sizning bepul limit tugadi.\nPremium olish uchun yozing 💰"
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

        # faqat muvaffaqiyatli bo‘lsa kamayadi
        user_limits[user_id] -= 1

    except Exception as e:
        bot_reply = f"Xatolik: {e}"

    await update.message.reply_text(
        f"{bot_reply}\n\n🧠 Qoldi: {user_limits[user_id]}"
    )

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 InspiRocketBot ishga tushdi...")
app.run_polling()
