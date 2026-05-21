# advanced_bot.py - Your Telegram Bingo Bot

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== CONFIGURATION - UPDATE THESE 3 LINES! ==========
BOT_TOKEN = "8423271349:AAGIeHFDKh4-phGJ_W9ao65N-YlDgZSyS10"  # Get from @BotFather on Telegram
WEBAPP_URL = "https://andromeda-bingo-bot-2.onrender.com"  # Your render URL
OWNER_ID = 840648715  # Your Telegram ID (get from @userinfobot)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with WebApp button"""
    user = update.effective_user
    
    welcome_text = f"""
🎉 *WELCOME TO ANDROID BINGO!* 🎉

Hello {user.first_name}!

💰 *Game Features:*
• Play with ETB currency
• Games start every 30 seconds
• Win 80% of prize pool!
• 20% supports community

👇 *Click below to start playing!* 👇
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 PLAY ANDROID BINGO", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("💰 Balance", callback_data='balance'),
         InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    
    # Add owner button if you're the owner
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data='owner')])
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown', 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 *Your Balance*\n\nOpen the game to see your balance!",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎮 *HOW TO PLAY BINGO*

1️⃣ Click PLAY ANDROID BINGO button
2️⃣ Choose stake (10/20/50 ETB)
3️⃣ Pick your lucky Cartela number
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
    
    import requests
    try:
        resp = requests.get('http://localhost:5000/api/owner_balance')
        data = resp.json()
        await update.message.reply_text(
            f"👑 *Owner Dashboard*\n\n"
            f"💰 Balance: {data['owner_balance']:.2f} ETB\n"
            f"📊 Total Commission: {data['total_commission_earned']:.2f} ETB\n"
            f"🎮 Games Hosted: {data['total_games_hosted']}\n"
            f"📈 Rate: {data['commission_rate']:.0f}%",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ Server error. Make sure Flask is running!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'balance':
        await balance_command(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'owner':
        await owner_command(update, context)

def main():
    print("=" * 50)
    print("🎉 ANDROID BINGO BOT")
    print("=" * 50)
    print(f"🌐 WebApp: {WEBAPP_URL}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("owner", owner_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Bot is running! Type /start on Telegram")
    app.run_polling()

if __name__ == '__main__':
    main()