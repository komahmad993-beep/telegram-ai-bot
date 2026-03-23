from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import os
from datetime import datetime

# ===== CONFIG =====
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 365165021  # <-- o'zingni telegram ID qo'y

# ===== DATABASE (oddiy RAM storage) =====
user_data = {}
premium_users = set()
all_users = set()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Salom! Men InspiRocketBot\n\n🤖 Savol ber — javob ol\n🎁 Kuniga 15 ta bepul"
    )

# ===== HANDLE MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    username = update.message.from_user.username or "no_username"

    # userlarni yig'amiz
    all_users.add(user_id)

    # LOG
    print(f"{user_id} (@{username}): {user_text}")

    # ADMINGA XABAR
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"👤 {user_id} (@{username})\n💬 {user_text}"
    )

    today = datetime.now().date()

    # ===== LIMIT SYSTEM =====
    if user_id not in premium_users:

        if user_id not in user_data:
            user_data[user_id] = {"date": today, "limit": 15}

        if user_data[user_id]["date"] != today:
            user_data[user_id]["date"] = today
            user_data[user_id]["limit"] = 15

        if user_data[user_id]["limit"] <= 0:
            keyboard = [
                [InlineKeyboardButton("💰 Premium olish", url="https://t.me/@phenomenal_ak")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🚫 Kunlik limit tugadi.\nPremium olish uchun bosing 👇",
                reply_markup=reply_markup
            )
            return

    # ===== AI JAVOB =====
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_text}
            ]
        )

        bot_reply = response.choices[0].message.content

        # limit kamayadi (faqat free user)
        if user_id not in premium_users:
            user_data[user_id]["limit"] -= 1

    except Exception as e:
        bot_reply = f"Xatolik: {e}"

    # ===== LIMIT INFO =====
    if user_id in premium_users:
        info = "♾ Premium"
    else:
        info = f"{user_data[user_id]['limit']}/15"

    await update.message.reply_text(
        f"{bot_reply}\n\n🧠 Qoldi: {info}"
    )

# ===== ADMIN: PREMIUM BERISH =====
async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    target_id = int(context.args[0])
    premium_users.add(target_id)

    await update.message.reply_text(f"✅ {target_id} premium bo‘ldi")

# ===== ADMIN: STATISTIKA =====
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    total = len(all_users)
    premium = len(premium_users)

    await update.message.reply_text(
        f"📊 Statistika:\n👥 Users: {total}\n💰 Premium: {premium}"
    )

# ===== ADMIN: PREMIUM LIST =====
async def premium_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not premium_users:
        await update.message.reply_text("❌ Premium user yo‘q")
        return

    users = "\n".join(map(str, premium_users))
    await update.message.reply_text(f"💰 Premium users:\n{users}")

# ===== APP =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addpremium", add_premium))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("premiumlist", premium_list))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 InspiRocketBot ishga tushdi...")
app.run_polling()
