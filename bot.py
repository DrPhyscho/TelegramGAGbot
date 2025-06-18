import asyncio
import logging
import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import pytz
import os
import nest_asyncio

# Configuration
TOKEN = '7782209619:AAELIyg4HTcOv58K5yObibFVyC44S3s3TM4'
CHAT_ID = '6172646907'
STOCK_URL = 'https://api.joshlei.com/v2/growagarden/stock'

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State
last_stock = {}
user_preferences = set()

# Emoji map
emoji_map = {
    "Carrot": "🥕", "Strawberry": "🍓", "Blueberry": "🍇", "Tomato": "🍅", "Corn": "🌽",
    "Daffodil": "🌼", "Watermelon": "🍉", "Pumpkin": "🎃", "Apple": "🍎", "Bamboo": "🍋",
    "Coconut": "🥥", "Cactus": "🌵", "Dragon Fruit": "🐉", "Grape": "🍇", "Mushroom": "🍄",
    "Pepper": "🌶️", "Cacao": "🍫", "Bean Stalk": "🥒", "Ember Lily": "🔥",
    "Lavender Seed": "💜", "Nectarshade Seed": "🌸", "Flower Seed Pack": "🌻",
    "Nectarine Seed": "🍑", "Hive Fruit Seed": "🐝", "Orange Tulip": "🦚",
    "Watering Can": "🚿", "Recall Wrench": "🔧", "Trowel": "🥄", "Basic Sprinkler": "🚶",
    "Advanced Sprinkler": "🚷", "Godly Sprinkler": "⚡", "Lightning Rod": "🌩️",
    "Master Sprinkler": "👑", "Favourite Tool": "⭐", "Harvest Tool": "✂️",
    "Friendship Pot": "🤝", "Pollen Radar": "📱", "Nectar Staff": "🌟", "Honey Sprinkler": "🍯",
    "Bee Crate": "📦", "Honey Walkway": "🛏️", "Honey Comb": "🍯", "Bee Chair": "🪑", "Cleaning Spray": "🔫",
    "Honey Torch": "🕯️",
    "Common Egg": "⚪", "Uncommon Egg": "🟢", "Rare Egg": "🔵", "Legendary Egg": "🔹",
    "Mythical Egg": "🔴", "Bug Egg": "🐛", "Bee Egg": "🐝"
}

all_items = list(emoji_map.keys())

# --- Helper Functions ---

async def fetch_from_api():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STOCK_URL, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        logger.error(f"API fetch failed: {e}")
        return None

def format_stock(title, items):
    message = f"*{title.upper()}*\n"
    for item in items:
        name = item.get("display_name", "Unknown")
        qty = item.get("quantity", 0)
        emoji = emoji_map.get(name, "📦")
        message += f"{emoji} {name} x{qty}\n"
    return message

def build_message(stock_data):
    ph_time = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p")
    header = f"🕒 *New Stock Detected!*\n📅 Date & Time: `{ph_time}`\n\n"
    parts = []

    for section in ["seed_stock", "gear_stock", "egg_stock", "cosmetic_stock"]:
        items = stock_data.get(section, [])
        filtered = [item for item in items if item.get("display_name") in user_preferences]
        if filtered:
            parts.append(format_stock(section.replace('_', ' ').title(), filtered))

    return header + "\n\n".join(parts)

# --- Command Handlers ---

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for item in all_items:
        emoji = emoji_map.get(item, "📦")
        keyboard.append([InlineKeyboardButton(f"{emoji} {item}", callback_data=item)])

    await update.message.reply_text("Select items to get notified for:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    item = query.data
    if item in user_preferences:
        user_preferences.remove(item)
        await query.edit_message_text(text=f"❌ Removed *{item}* from notification list.", parse_mode=ParseMode.MARKDOWN)
    else:
        user_preferences.add(item)
        await query.edit_message_text(text=f"✅ Added *{item}* to notification list.", parse_mode=ParseMode.MARKDOWN)

async def notifylist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_preferences:
        await update.message.reply_text("You have not selected any items yet.")
        return

    msg = "*Your Selected Notification Items:*\n"
    for item in sorted(user_preferences):
        emoji = emoji_map.get(item, "📦")
        msg += f"{emoji} {item}\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ph_time = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p")
    item_count = len(user_preferences)
    item_list = '\n'.join([f"{emoji_map.get(item, '📦')} {item}" for item in sorted(user_preferences)])

    message = (
        "✅ *Bot Status: Alive*\n"
        f"🕒 *Current Time (PH)*: `{ph_time}`\n"
        f"📦 *Tracking {item_count} item(s)*\n"
    )

    if item_count:
        message += "\n🔔 *Items Being Tracked:*\n" + item_list

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# --- Background Task ---

async def stock_monitor(bot: Bot):
    global last_stock
    while True:
        logger.info("✅ Checking for new stock...")
        stock = await fetch_from_api()
        if stock:
            matched = []
            for section in ["seed_stock", "gear_stock", "egg_stock", "cosmetic_stock"]:
                matched.extend([item for item in stock.get(section, []) if item.get("display_name") in user_preferences])

            if matched and stock != last_stock:
                logger.info("📦 New stock detected, sending a message...")
                message = build_message(stock)
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
                    last_stock = stock
                except Exception as e:
                    logger.error(f"❌ Telegram send failed: {e}")
        await asyncio.sleep(15)

# --- Health Check Server ---

async def healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)  # <- Required for Railway
    await site.start()
    logger.info("🌐 Health check server running on http://0.0.0.0:8080")

# --- Main Entry ---

async def main():
    bot = Bot(TOKEN)
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("notify", notify_command))
    app.add_handler(CommandHandler("notifylist", notifylist_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await start_webserver()
    asyncio.create_task(stock_monitor(bot))

    logger.info("🚀 GrowAGarden bot + server is running...")
    await app.updater.idle()

if __name__ == "__main__":
    nest_asyncio.apply()
    logger.info("🎯 Starting GrowAGarden bot...")
    asyncio.run(main())
