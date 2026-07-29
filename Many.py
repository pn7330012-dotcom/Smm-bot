import os
import sqlite3
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Configuration Variables
MASTER_BOT_TOKEN = os.environ.get("BOT_TOKEN")
SMM_API_KEY = os.environ.get("SMM_API_KEY")
SMM_API_URL = os.environ.get("SMM_API_URL", "https://smmmain.com/api/v2")

# Database Setup
def init_db():
    conn = sqlite3.connect("smm_bot.db")
    cursor = conn.cursor()
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0
        )
    """)
    # Child Bots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS child_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            bot_token TEXT UNIQUE,
            margin REAL DEFAULT 10.0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Helper for SMM API Balance Check
def get_smm_balance():
    try:
        res = requests.post(SMM_API_URL, data={"key": SMM_API_KEY, "action": "balance"}).json()
        return res.get("balance", "0"), res.get("currency", "USD")
    except Exception:
        return "N/A", "USD"

# Start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Register User
    conn = sqlite3.connect("smm_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("📦 Services", callback_data="services"), InlineKeyboardButton("💳 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("🤖 Create Child Bot (Clone)", callback_data="create_child")],
        [InlineKeyboardButton("📊 My Child Bots", callback_data="my_childs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 **Welcome to SMM Master Reseller Bot!**\n\n"
        f"Aap yahan se SMM services buy kar sakte hain ya apna khud ka **Child Bot (Clone)** bana kar earn kar sakte hain!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Callback Button Handler
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "wallet":
        conn = sqlite3.connect("smm_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]
        conn.close()
        
        await query.edit_message_text(
            f"💳 **Aapka Balance:** ${bal:.2f}\n\nBalance add karne ke liye Admin se contact karein.",
            parse_mode="Markdown"
        )

    elif query.data == "create_child":
        context.user_data["awaiting_token"] = True
        await query.edit_message_text(
            "🤖 **Create Child Bot:**\n\n"
            "1. Telegram par `@BotFather` par jayein.\n"
            "2. `/newbot` karke naya bot banayein.\n"
            "3. Wahan se milne wala **API Token** mujhe yahan reply me bhejein:"
        )

    elif query.data == "my_childs":
        conn = sqlite3.connect("smm_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT bot_token FROM child_bots WHERE owner_id = ?", (user_id,))
        bots = cursor.fetchall()
        conn.close()

        if bots:
            msg = f"📊 **Aapke Registered Child Bots ({len(bots)}):**\n\n"
            for b in bots:
                msg += f"• Token: `{b[0][:10]}...` (Active)\n"
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Aapne abhi tak koi Child Bot nahi banaya hai.")

    elif query.data == "services":
        bal, curr = get_smm_balance()
        await query.edit_message_text(f"📦 **Main Panel Status:** Connected\n💳 Panel Balance: {bal} {curr}")

# Text Handler for Token Input
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if context.user_data.get("awaiting_token"):
        if ":" in text and len(text) > 30:
            token = text
            conn = sqlite3.connect("smm_bot.db")
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO child_bots (owner_id, bot_token) VALUES (?, ?)", (user_id, token))
                conn.commit()
                conn.close()
                
                context.user_data["awaiting_token"] = False
                await update.message.reply_text("✅ **Child Bot Successfully Registered!**\n\nAapka clone bot ab live ho chuka hai.")
            except sqlite3.IntegrityError:
                conn.close()
                await update.message.reply_text("⚠️ Ye Bot Token pehle se registered hai!")
        else:
            await update.message.reply_text("❌ Invalid Token format! Kripya sahi Token bhejein.")

# Main Runner
def main():
    app = Application.builder().token(MASTER_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🚀 Master SMM Bot System Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
