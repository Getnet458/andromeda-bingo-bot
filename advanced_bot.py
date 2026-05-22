# advanced_bot.py - Production version for Render

import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import Conflict

# ========== CONFIGURATION - READ FROM ENVIRONMENT ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8423271349:AAGIeHFDKh4-phGJ_W9ao65N-YlDgZSyS10")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://andromeda-bingo-bot.onrender.com")
OWNER_ID = int(os.environ.get("OWNER_ID", " 840648715"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask server URL (internal - Render handles this)
FLASK_URL = os.environ.get("FLASK_URL", "http://localhost:5000")

def call_flask_api(endpoint, method='GET', data=None):
    """Make API calls to Flask server"""
    try:
        # In production, use the Render URL
        base_url = WEBAPP_URL if os.environ.get("RENDER") else "http://localhost:5000"
        url = f"{base_url}{endpoint}"
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"API error: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_text = f"""
🎉 *ANDROMEDA BINGO* 🎉

Hello {user.first_name}!

💰 *Game Features:*
• Play with ETB currency
• Games start every 30 seconds
• Win 80% of prize pool!
• 20% to community

👇 *Click below to play!* 👇
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 PLAY ANDROMEDA BINGO", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("💰 Balance", callback_data='balance'),
         InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data='owner')])
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = call_flask_api('/api/balance', method='POST', data={'user_id': user.id})
    
    if data:
        await update.message.reply_text(
            f"💰 *Your Balance*\n\nAvailable: **{data.get('balance', 0):.0f} ETB**\n"
            f"Total Won: **{data.get('total_won', 0):.0f} ETB**\n"
            f"Games Won: **{data.get('games_won', 0)}**",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("💰 Check balance in the game!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎮 *HOW TO PLAY*

1️⃣ Click PLAY ANDROMEDA BINGO
2️⃣ Choose stake (10/20/50 ETB)
3️⃣ Pick lucky Cartela number
4️⃣ Game starts in 30 seconds
5️⃣ Numbers draw automatically
6️⃣ Complete BINGO to WIN!

*Commands:*
/start - Main menu
/balance - Check balance
/help - This menu

Good luck! 🍀
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def owner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    data = call_flask_api('/api/owner_balance', method='GET')
    if data:
        await update.message.reply_text(
            f"👑 *Owner Dashboard*\n\n"
            f"💰 Balance: {data['owner_balance']:.2f} ETB\n"
            f"📊 Total Commission: {data['total_commission_earned']:.2f} ETB\n"
            f"🎮 Games Hosted: {data['total_games_hosted']}\n"
            f"📈 Rate: {data['commission_rate']:.0f}%",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("👑 Owner Panel - Bot is running!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'balance':
        user = update.effective_user
        data = call_flask_api('/api/balance', method='POST', data={'user_id': user.id})
        if data:
            await query.edit_message_text(
                f"💰 Balance: **{data.get('balance', 0):.0f} ETB**",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("💰 Open game to see balance!")
    elif query.data == 'help':
        await query.edit_message_text("Click PLAY ANDROMEDA BINGO to start!")
    elif query.data == 'owner':
        user = update.effective_user
        if user.id == OWNER_ID:
            await query.edit_message_text("👑 Owner Panel - Bot is running!\n💰 20% commission active")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ Error. Type /start to continue.")

def main():
    print("=" * 50)
    print("🎮 ANDROMEDA BINGO BOT")
    print("=" * 50)
    print(f"🌐 WebApp URL: {WEBAPP_URL}")
    print(f"👤 Owner ID: {OWNER_ID}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Clear any existing webhook (important!)
    try:
        app.bot.delete_webhook()
        print("✅ Webhook cleared")
    except Exception as e:
        print(f"Webhook clear: {e}")
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    print("✅ Bot is running! Type /start on Telegram")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()