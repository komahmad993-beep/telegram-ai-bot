from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os
from datetime import datetime

# ===== CONFIG =====
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 365165021  # o'zingni telegram id

# ===== DATABASE (oddiy dict hozircha) =====
user_data = {}
premium_users = set()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    await update.message.reply_text(
        "🚀 Salom!\n\n"
        "🤖 Men AI yordamchi botman\n"
        "💡 Savollarga javob beraman\n"
        "🧠 Kunlik limit: 2 ta\n\n"
        "Savol ber 👇"
    )

# ===== MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "no_username"
    user_text = update.message.text

    print(f"{user_id} (@{username}): {user_text}")

    today = datetime.now().date()

    # ===== USER INIT =====
    if user_id not in user_data:
        user_data[user_id] = {
            "date": today,
            "limit": 2
        }

    # ===== RESET DAILY =====
    if user_data[user_id]["date"] != today:
        user_data[user_id]["date"] = today
        user_data[user_id]["limit"] = 2

    # ===== LIMIT CHECK =====
    if user_id not in premium_users:
        if user_data[user_id]["limit"] <= 0:
            keyboard = [
                [InlineKeyboardButton("💰 Premium olish", url="https://t.me/your_username")]
            ]

            await update.message.reply_text(
                "🚫 Limit tugadi (2 ta)\nPremium olish uchun yozing 👇",
                reply_markup=InlineKeyboardMarkup(keyboard)
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

        # ===== LIMIT MINUS =====
        if user_id not in premium_users:
            user_data[user_id]["limit"] -= 1

    except Exception as e:
        bot_reply = f"Xatolik: {e}"

    # ===== INFO =====
    if user_id in premium_users:
        info = "♾ Premium"
    else:
        info = f"{user_data[user_id]['limit']}/2"

    await update.message.reply_text(
        f"{bot_reply}\n\n🧠 Qoldi: {info}"
    )

    # ===== ADMIN LOG =====
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"👤 {user_id} (@{username})\n💬 {user_text}"
    )

# ===== ADD PREMIUM (ADMIN) =====
async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
        premium_users.add(target_id)

        await update.message.reply_text(f"✅ {target_id} premium bo‘ldi")
    except:
        await update.message.reply_text("Xato format. Masalan:\n/addpremium 123456789")

# ===== RUN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addpremium", add_premium))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot ishlayapti...")
    app.run_polling()
