import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os
from datetime import datetime
import threading

# ===== CONFIG =====
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 365165021

# ===== DATABASE =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    last_date TEXT,
    limit_count INTEGER,
    is_premium INTEGER DEFAULT 0
)
""")
conn.commit()

# ===== TELEGRAM BOT =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"🚀 Salom!\n🆔 Sizning ID: {user_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "no_username"
    user_text = update.message.text

    print(f"{user_id} (@{username}): {user_text}")

    today = str(datetime.now().date())

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
            (user_id, username, today, 2, 0)
        )
        conn.commit()
        limit = 2
        is_premium = 0
    else:
        _, _, last_date, limit, is_premium = user

        if last_date != today:
            limit = 15
            cursor.execute(
                "UPDATE users SET last_date=?, limit_count=? WHERE user_id=?",
                (today, limit, user_id)
            )
            conn.commit()

    if not is_premium and limit <= 0:
        keyboard = [
            [InlineKeyboardButton("💰 Premium olish", url="https://t.me/your_username")]
        ]
        await update.message.reply_text(
            "🚫 Limit tugadi",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_text}]
        )
        bot_reply = response.choices[0].message.content

        if not is_premium:
            limit -= 1
            cursor.execute(
                "UPDATE users SET limit_count=? WHERE user_id=?",
                (limit, user_id)
            )
            conn.commit()

    except Exception as e:
        bot_reply = str(e)

    info = "♾ Premium" if is_premium else f"{limit}/2"

    await update.message.reply_text(f"{bot_reply}\n\n🧠 Qoldi: {info}")

# ===== FLASK SERVER =====
app_flask = Flask(__name__)

@app_flask.route("/payment", methods=["POST"])
def payment():
    data = request.json

    # BU YERGA CLICK DATA KELADI
    user_id = int(data.get("user_id"))

    cursor.execute(
        "UPDATE users SET is_premium=1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()

    return {"status": "ok"}

# ===== TELEGRAM RUN =====
def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot ishlayapti...")
    app.run_polling()

# ===== RUN BOTH =====
threading.Thread(target=run_bot).start()

app_flask.run(host="0.0.0.0", port=8080)
