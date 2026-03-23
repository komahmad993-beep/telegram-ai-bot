import sqlite3
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os
from datetime import datetime, timedelta
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
    is_premium INTEGER DEFAULT 0,
    premium_until TEXT,
    reminded INTEGER DEFAULT 0,
    total_paid INTEGER DEFAULT 0
)
""")
conn.commit()

# ===== TELEGRAM BOT =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(
        f"🚀 Salom!\n\n🤖 AI yordamchi bot\n🎁 Kuniga 2 ta bepul\n\n🆔 ID: {user_id}"
    )

# ===== HANDLE MESSAGE =====
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
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, today, 2, 0, None, 0, 0)
        )
        conn.commit()
        limit = 2
        premium_until = None
    else:
        _, _, last_date, limit, is_premium, premium_until, _, _ = user

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

    await update.message.reply_text(f"✅ Premium: {expire_date}")

# ===== FLASK =====
app_flask = Flask(__name__)

# ===== WEB CHAT API =====
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

# ===== PAYMENT =====
@app_flask.route("/payment", methods=["POST"])
def payment():
    data = request.json or {}
    user_id = int(data.get("user_id", 0))

    if user_id == 0:
        return {"error": "no user_id"}

    cursor.execute("SELECT premium_until FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()

    if result and result[0]:
        old_date = datetime.strptime(result[0], "%Y-%m-%d")
        new_date = old_date + timedelta(days=30) if old_date > datetime.now() else datetime.now() + timedelta(days=30)
    else:
        new_date = datetime.now() + timedelta(days=30)

    expire_date = new_date.strftime("%Y-%m-%d")

    cursor.execute(
        "UPDATE users SET is_premium=1, premium_until=?, total_paid=total_paid+1 WHERE user_id=?",
        (expire_date, user_id)
    )
    conn.commit()

    print(f"💰 PAYMENT: {user_id} → {expire_date}")

    return {"status": "ok"}

# ===== DASHBOARD =====
@app_flask.route("/admin")
def admin_panel():
    password = request.args.get("pass")

    if password != "1234":
        return "❌ Access denied"

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")
    premium = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_paid) FROM users")
    payments = cursor.fetchone()[0] or 0

    income = payments * 20000

    return f"""
    <h1>🚀 Dashboard</h1>
    <p>Users: {total}</p>
    <p>Premium: {premium}</p>
    <p>Payments: {payments}</p>
    <p>Income: {income} so'm</p>
    """

# ===== TELEGRAM RUN =====
def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addpremium", add_premium))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot ishlayapti...")
    app.run_polling()

# ===== RUN =====
threading.Thread(target=run_bot).start()

app_flask.run(host="0.0.0.0", port=8080)
