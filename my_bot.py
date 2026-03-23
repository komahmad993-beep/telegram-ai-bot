import sqlite3
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os
from datetime import datetime, timedelta
import threading

# ===== CONFIG =====
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 365165021

VIDEO_URL = "https://your-video-link.mp4"  # video link qo'y

# ===== DATABASE =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    last_date TEXT,
    limit_count INTEGER,
    is_premium INTEGER DEFAULT 0,
    premium_until TEXT
)
""")
conn.commit()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    await update.message.reply_video(
        video=VIDEO_URL,
        caption="🎥 Bot qanday ishlaydi"
    )

    keyboard = [
        ["✈️ Bilet", "🏨 Hotel"],
        ["🚗 Mashina", "ℹ️ Yordam"]
    ]

    await update.message.reply_text(
        f"🚀 InspiRocket AI\n\n2 ta bepul savol\nID: {user_id}",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===== MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    today = str(datetime.now().date())

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "", today, 2, 0, None)
        )
        conn.commit()
        limit = 2
    else:
        _, _, last_date, limit, is_premium, premium_until = user

        if last_date != today:
            limit = 2
            cursor.execute(
                "UPDATE users SET last_date=?, limit_count=? WHERE user_id=?",
                (today, limit, user_id)
            )
            conn.commit()

    # premium check
    is_premium = False
    if user and user[5]:
        expire = datetime.strptime(user[5], "%Y-%m-%d")
        if expire > datetime.now():
            is_premium = True

    if not is_premium and limit <= 0:
        await update.message.reply_text("🚫 Limit tugadi")
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

    await update.message.reply_text(bot_reply)

# ===== FLASK =====
app_flask = Flask(__name__)

@app_flask.route("/chat", methods=["POST"])
def chat():
    data = request.json
    msg = data.get("message", "")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": msg}]
    )

    return jsonify({"reply": response.choices[0].message.content})

# ===== RUN =====
def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

threading.Thread(target=run_bot).start()

port = int(os.environ.get("PORT", 8080))
app_flask.run(host="0.0.0.0", port=port)
