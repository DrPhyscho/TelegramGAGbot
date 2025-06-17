import asyncio
import logging
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
from datetime import datetime
import pytz  # Required for timezone support

TOKEN = '7782209619:AAELIyg4HTcOv58K5yObibFVyC44S3s3TM4'
CHAT_ID = '6172646907'
STOCK_URL = 'https://api.joshlei.com/v2/growagarden/stock'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

last_stock = {}

# Emoji map
emoji_map = {
    # Seeds
    "Carrot": "🥕", "Strawberry": "🍓", "Blueberry": "🍇", "Tomato": "🍅", "Corn": "🌽",
    "Daffodil": "🌼", "Watermelon": "🍉", "Pumpkin": "🎃", "Apple": "🍎", "Bamboo": "🎋",
    "Coconut": "🥥", "Cactus": "🌵", "Dragon Fruit": "🐉", "Grape": "🍇", "Mushroom": "🍄",
    "Pepper": "🌶️", "Cacao": "🍫", "Bean Stalk": "🥒", "Ember Lily": "🔥",
    "Lavender Seed": "💜", "Nectarshade Seed": "🌸", "Flower Seed Pack": "🌻",
    "Nectarine Seed": "🍑", "Hive Fruit Seed": "🐝","Orange Tulip": "🧡",
    # Gear
    "Watering Can": "🚿", "Recall Wrench": "🔧", "Trowel": "🥄", "Basic Sprinkler": "💦",
    "Advanced Sprinkler": "💧", "Godly Sprinkler": "⚡", "Lightning Rod": "🌩️",
    "Master Sprinkler": "👑", "Favourite Tool": "⭐", "Harvest Tool": "✂️",
    "Friendship Pot": "🤝", "Pollen Radar": "📡", "Nectar Staff": "🌟", "Honey Sprinkler": "🍯",
    "Bee Crate": "📦", "Honey Walkway": "🛤️", "Honey Comb": "🍯", "Bee Chair": "🪑", "Cleaning Spray": "🔫",
    "Honey Torch": "🕯",
    # Eggs
    "Common Egg": "⚪", "Uncommon Egg": "🟢", "Rare Egg": "🔵", "Legendary Egg": "🟣",
    "Mythical Egg": "🔴", "Bug Egg": "🐛", "Bee Egg": "🐝"
}


def format_stock(title, items):
    message = f"*{title.upper()}*\n"
    for item in items:
        name = item.get("display_name", "Unknown")
        qty = item.get("quantity", 0)
        emoji = emoji_map.get(name, "📦")
        message += f"{emoji} {name} x{qty}\n"
    return message

def build_message(stock_data):
    # Get current time in Asia/Manila timezone using 12-hour format
    ph_time = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p")
    header = f"🕒 *New Stock Detected!*\n📅 Date & Time: `{ph_time}`\n\n"

    parts = []
    if "seed_stock" in stock_data:
        parts.append(format_stock("Seed Stock", stock_data["seed_stock"]))
    if "gear_stock" in stock_data:
        parts.append(format_stock("Gear Stock", stock_data["gear_stock"]))
    if "egg_stock" in stock_data:
        parts.append(format_stock("Egg Stock", stock_data["egg_stock"]))
    if "cosmetic_stock" in stock_data:
        parts.append(format_stock("Cosmetic Stock", stock_data["cosmetic_stock"]))

    return header + "\n\n".join(parts)

async def fetch_from_api():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(STOCK_URL, timeout=10) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        logger.error(f"API fetch failed: {e}")
        return None

async def main_loop():
    bot = Bot(token=TOKEN)
    global last_stock

    while True:
        stock = await fetch_from_api()

        if stock:
            if stock != last_stock:
                logger.info("New stock detected. Sending to Telegram...")
                message = build_message(stock)
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
                    last_stock = stock
                except Exception as e:
                    logger.error(f"Telegram send failed: {e}")
            else:
                logger.info("Stock has not changed.")
        else:
            logger.warning("Stock fetch failed.")

        await asyncio.sleep(60)

if __name__ == "__main__":
    logger.info("GrowAGarden Telegram bot started.")
    asyncio.run(main_loop())
