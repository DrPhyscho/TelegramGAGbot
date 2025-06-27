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

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# State
last_stock = {}
user_preferences = set()

# Emoji Map
emoji_map = {
    "Carrot": "🥕", "Strawberry": "🍓", "Blueberry": "🫐", "Tomato": "🍅", "Cauliflower": "🥬",
    "Watermelon": "🍉", "Green apple": "🍏", "Avocado": "🥑", "Banana": "🍌", "Pineapple": "🍍",
    "Kiwi": "🥝", "Bell pepper": "🫑", "Prickly pear": "🌵", "Loquat": "🍑🌿", "Feijoa": "🍈", "Sugar apple": "🍬🍏",

    "Common Summer Egg": "🏖️⚪🥚", "Rare Summer Egg": "🏖️🔵🥚", "Paradise Egg": "🌴🏖️🥚",
    "Common Egg": "⚪🥚", "Uncommon Egg": "🟢🥚", "Rare Egg": "🔵🥚",
    "Legendary Egg": "🔹🥚", "Mythical Egg": "🔴🥚", "Bug Egg": "🐛🥚",

    "Godly Sprinkler": "💦⚡", "Tanning Mirror": "🪞", "Lightning Rod": "⚡", "Master Sprinkler": "👑💦",
    "Watering Can": "🚿", "Recall Wrench": "🔧", "Trowel": "📦", "Basic Sprinkler": "💧",
    "Advanced Sprinkler": "💦", "Favourite Tool": "⭐", "Harvest Tool": "✂️", "Friendship Pot": "🤝",

    "Cosmetic": "📦",
}

# All possible items
all_items = list(emoji_map.keys())

def normalize_name(name):
    return name.strip().casefold()

def filter_relevant_stock(stock):
    relevant = {}
    for section in ["seed_stock", "gear_stock", "egg_stock", "cosmetic_stock"]:
        items = stock.get(section, [])
        filtered = [item for item in items if normalize_name(item.get("display_name", "")) in {normalize_name(p) for p in user_preferences}]
        if filtered:
            relevant[section] = sorted(filtered, key=lambda x: normalize_name(x.get("display_name", "")))
    return relevant

def format_stock(title, items):
    message = f"*{title.upper()}*\n"
    for item in items:
        name = item.get("display_name", "Unknown")
        qty = item.get("quantity", 0)
        emoji = emoji_map.get(name, "📦")
        message += f"{emoji} {name} x{qty}\n"
    return message

def build_message(filtered_stock):
    ph_time = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p")
    header = f"🕒 *New Stock Detected!*\n🗓️ Date & Time: `{ph_time}`\n\n"
    parts = [format_stock(section.replace('_', ' ').title(), items) for section, items in filtered_stock.items()]
    return header + "\n\n".join(parts)

async def fetch_from_api():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STOCK_URL, timeout=10) as resp:
                remaining_ip = resp.headers.get("Ratelimit-Remaining-Ip")
                remaining_global = resp.headers.get("Ratelimit-Remaining-Global")
                retry_after = resp.headers.get("Retry-After")

                logger.info(f"📊 Ratelimit IP: {remaining_ip}, Global: {remaining_global}")
                if retry_after:
                    return None, remaining_ip, remaining_global, int(retry_after)

                resp.raise_for_status()
                return await resp.json(), remaining_ip, remaining_global, None
    except Exception as e:
        logger.error(f"API fetch failed: {e}")
        return None, None, None, None

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{emoji_map.get(item, '📦')} {item}", callback_data=item)]
        for item in all_items
    ]
    await update.message.reply_text(
        "🔔 Select items to get notified for (tap to toggle):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item = query.data
    if item in user_preferences:
        user_preferences.remove(item)
        await query.edit_message_text(f"❌ Removed *{item}* from your list.", parse_mode=ParseMode.MARKDOWN)
    else:
        user_preferences.add(item)
        await query.edit_message_text(f"✅ Added *{item}* to your list.", parse_mode=ParseMode.MARKDOWN)

async def notifylist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_preferences:
        await update.message.reply_text("📭 You haven't selected any items.")
        return
    msg = "*Your Selected Items:*\n" + "\n".join([f"{emoji_map.get(item, '📦')} {item}" for item in sorted(user_preferences)])
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ph_time = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p")
    items = '\n'.join([f"{emoji_map.get(item, '📦')} {item}" for item in sorted(user_preferences)])
    msg = f"✅ *Bot is Alive!*\n🕒 Time (PH): `{ph_time}`\n🔔 Tracking {len(user_preferences)} item(s).\n"
    if user_preferences:
        msg += f"\n📦 *Items:* \n{items}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def stock_monitor(bot: Bot):
    global last_stock
    wait_time = 30
    sent_limit_alert = False

    while True:
        logger.info("🔍 Checking stock...")
        stock, rem_ip, rem_global, wait_override = await fetch_from_api()

        if wait_override:
            await asyncio.sleep(wait_override)
            continue

        if stock:
            filtered = filter_relevant_stock(stock)
            if filtered and filtered != last_stock:
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=build_message(filtered), parse_mode=ParseMode.MARKDOWN)
                    last_stock = filtered
                except Exception as e:
                    logger.error(f"Telegram send failed: {e}")

        try:
            ip = int(rem_ip) if rem_ip else 10000
            glob = int(rem_global) if rem_global else 100000

            if ip < 10 or glob < 100:
                if not sent_limit_alert:
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"⚠️ *Warning:* API rate limit near!\nIP: {ip}, Global: {glob}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    sent_limit_alert = True
                wait_time = 180
            elif ip < 100 or glob < 500:
                wait_time = 60
                sent_limit_alert = False
            else:
                wait_time = 30
                sent_limit_alert = False
        except:
            wait_time = 30

        await asyncio.sleep(wait_time)

async def healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("🌐 Healthcheck server on port 8080")

async def main():
    logger.info("🚀 Starting GrowAGarden Bot...")
    bot = Bot(TOKEN)
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("notify", notify_command))
    app.add_handler(CommandHandler("notifylist", notifylist_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    await start_webserver()
    asyncio.create_task(stock_monitor(bot))
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
