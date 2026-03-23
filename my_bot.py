from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_data = {}
premium_users = set()

ADMIN_ID = 365165021


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Salom! Men @InspiRocketBot")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    username = update.message.from_user.username or "no_username"

    # LOG
    print(f"{user_id} (@{username}): {user_text}")

    # ADMINGA YUBORISH
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"👤 {user_id} (@{username})\n💬 {user_text}"
    )

    today = datetime.now().date()

    # PREMIUM EMAS BO‘LSA LIMIT ISHLAYDI
    if user_id not in premium_users:

        if user_id not in user_data:
            user_data[user_id] = {"date": today, "limit": 15}

        if user_data[user_id]["date"] != today:
            user_data[user_id]["date"] = today
            user_data[user_id]["limit"] = 15

        if user_data[user_id]["limit"] <= 0:
            await update.message.reply_text(
                "🚫 Kunlik limit tugadi.\n💰 Premium olish uchun yozing: @phenomenal_ak"
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

        # LIMITNI FAOL USERLARGA KAMAYTIRAMIZ
        if user_id not in premium_users:
            user_data[user_id]["limit"] -= 1

    except Exception as e:
        bot_reply = f"Xatolik: {e}"

    # QOLDIQ
    if user_id in premium_users:
        info = "♾ Premium"
    else:
        info = f"{user_data[user_id]['limit']}/15"

    await update.message.reply_text(
        f"{bot_reply}\n\n🧠 Qoldi: {info}"
    )


# ADMIN COMMAND
async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    target_id = int(context.args[0])
    premium_users.add(target_id)

    await update.message.reply_text(f"✅ {target_id} premium bo‘ldi")


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addpremium", add_premium))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 InspiRocketBot ishga tushdi...")
app.run_polling()
