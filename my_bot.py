from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from openai import OpenAI
import os
from datetime import datetime
import asyncio

# ===== CONFIG =====
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 365165021

# ===== DATA =====
user_data = {}
premium_users = set()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Salom!\n\n"
        "Bu oddiy bot emas — AI yordamchi\n"
    )

    await asyncio.sleep(1)

    keyboard = [
        [InlineKeyboardButton("🧠 Savol berish", callback_data="ask")],
        [InlineKeyboardButton("💎 Premium olish", callback_data="buy")]
    ]

    await update.message.reply_text(
        "👇 Boshlash:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ask":
        await query.message.reply_text("💬 Savolingizni yozing...")

    elif query.data == "buy":
        await buy_premium(update, context)

# ===== BUY PREMIUM =====
async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = [LabeledPrice("Premium (30 kun)", 1000)]  # 10 Stars

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="Premium obuna",
        description="30 kun unlimited AI",
        payload="premium",
        provider_token="",  # STARS uchun bo‘sh
        currency="XTR",
        prices=prices
    )

# ===== PAYMENT SUCCESS =====
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    premium_users.add(user_id)

    await update.message.reply_text("✅ Premium aktivatsiya qilindi!")

# ===== MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text

    today = datetime.now().date()

    if user_id not in user_data:
        user_data[user_id] = {"date": today, "limit": 2}

    if user_data[user_id]["date"] != today:
        user_data[user_id] = {"date": today, "limit": 2}

    if user_id not in premium_users and user_data[user_id]["limit"] <= 0:
        keyboard = [
            [InlineKeyboardButton("💰 Premium olish", callback_data="buy")]
        ]

        await update.message.reply_text(
            "🚫 Limit tugadi",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    msg = await update.message.reply_text("🤔 O‘ylayapman...")

    try:
        model = "gpt-4o-mini"
        if user_id in premium_users:
            model = "gpt-4o"

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_text}]
        )

        bot_reply = response.choices[0].message.content

        if user_id not in premium_users:
            user_data[user_id]["limit"] -= 1

    except Exception as e:
        bot_reply = str(e)

    await msg.delete()

    info = "♾ Premium" if user_id in premium_users else f"{user_data[user_id]['limit']}/2"

    await update.message.reply_text(f"{bot_reply}\n\n🧠 Qoldi: {info}")

# ===== ADMIN =====
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        f"👥 Users: {len(user_data)}\n💎 Premium: {len(premium_users)}"
    )

# ===== RUN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 BOT ISHLAYAPTI")
    app.run_polling()
