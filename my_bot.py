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

VIDEO_URL = "https://your-video-link.mp4"  # 🔥 shu yerga video link qo‘y

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

# ===== START (WELCOME + VIDEO) =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    text = f"""
🚀 InspiRocket AI ga xush kelibsiz!

🤖 Men sizga yordam beraman:
✈️ Bilet topish
🏨 Hotel qidirish
🚗 Mashina topish
🌐 Internetdan ma’lumot
🧠 AI javoblar

💰 Kuniga 2 ta bepul savol

🆔 ID: {user_id}

👇 Masalan yozing:
"Dubayga arzon bilet top"
"""

    # VIDEO
    await update.message.reply_video(
        video=VIDEO_URL,
        caption="🎥 Bot qanday ishlaydi"
    )

    # BUTTONS
    keyboard = [
        ["✈️ Bilet top", "🏨 Hotel"],
        ["🚗 Mashina", "ℹ️ Yordam"]
    ]

    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ===== MESSAGE =====
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
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, today, 2, 0, None)
        )
        conn.commit()
        limit = 2
        premium_until = None
    else:
        _, _, last_date, limit, is_premium, premium_until = user

        if last_date != today:
            limit = 2
            cursor.execute(
                "UPDATE users SET last_date=?, limit_count=? WHERE user_id=?",
                (today, limit, user_id)
            )
            conn.commit()

    # ===== PREMIUM CHECK =====
    is_premium = False
    if user and user[5]:
        expire = datetime.strptime(user[5], "%Y-%m-%d")
        if expire > datetime.now():
            is_premium = True

    # ===== LIMIT =====
    if not is_premium and limit <= 0:
        keyboard = [
            [InlineKeyboardButton("💰 Premium olish", url="https://t.me/InspiRocketBot")]
        ]
        await update.message.reply_text(
            "🚫 Limit tugadi (2 ta)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ===== AI =====
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
        bot_reply = f"Xatolik: {e}"

    # ===== INFO =====
    if is_premium:
        info = f"♾ Premium ({premium_until})"
    else:
        info = f"{limit}/2"

    await update.message.reply_text(f"{bot_reply}\n\n🧠 Qoldi: {info}")

# ===== ADMIN =====
async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    user_id = int(context.args[0])
    expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    cursor.execute(
        "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
        (expire_date, user_id)
    )
    conn.commit()

    await update.message.reply_text(f"✅ Premium berildi: {expire_date}")

# ===== FLASK =====
app_flask = Flask(__name__)

@app_flask.route("/chat", methods=["POST"])
def web_chat():
    data = request.json
    user_text = data.get("message", "")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_text}]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = str(e)

    return jsonify({"reply": reply})

@app_flask.route("/payment", methods=["POST"])
def payment():
    data = request.json or {}
    user_id = int(data.get("user_id", 0))

    expire_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    cursor.execute(
        "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
        (expire_date, user_id)
    )
    conn.commit()

    return {"status": "ok"}

# ===== RUN =====
def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addpremium", add_premium))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot ishlayapti...")
    app.run_polling()

threading.Thread(target=run_bot).start()

app_flask.run(host="0.0.0.0", port=8080)
