import base64
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.dbusers import db
from plugins.users_api import get_user, get_short_link
from plugins.database import get_file_details
from config import ADMINS, WEBSITE_URL, WEBSITE_URL_MODE, VERIFY_TUTORIAL

def get_premium_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL)],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")]
    ])

@Client.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)

    if len(message.command) == 1:
        await message.reply("Welcome! Send me a file to start.")
        return

    start_param = message.command[1]
    padding = '=' * (-len(start_param) % 4)

    try:
        first_decoded = base64.urlsafe_b64decode(start_param + padding).decode()
        # Agar pehla decode URL form mein hai (shortlink), to usme se start param extract karo
        if first_decoded.startswith("http"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(first_decoded)
            params = parse_qs(parsed.query)
            inner_start = params.get("start")
            if not inner_start:
                await message.reply("❌ Invalid start parameter in shortlink.")
                return
            inner_padding = '=' * (-len(inner_start[0]) % 4)
            decoded = base64.urlsafe_b64decode(inner_start[0] + inner_padding).decode()
        else:
            decoded = first_decoded
    except Exception:
        await message.reply("❌ Invalid start parameter.")
        return

    if decoded.startswith("file_"):
        file_id = decoded[5:]
        is_premium = await db.check_premium(user_id)
        file_data = await get_file_details(file_id)

        if not file_data:
            await message.reply("❌ File not found.")
            return

        if is_premium:
            await client.send_document(user_id, file_data['file_id'], caption=file_data.get('caption', ''))
        else:
            user = await get_user(user_id)
            bot_username = (await client.get_me()).username
            share_link = (f"{WEBSITE_URL}?Tech_VJ={start_param}" if WEBSITE_URL_MODE
                          else f"https://t.me/{bot_username}?start={start_param}")
            short_link = await get_short_link(user, share_link) if user.get("base_site") and user.get("shortener_api") else share_link
            await message.reply(f"🔗 Here is your short link for download:\n{short_link}", reply_markup=get_premium_buttons())
    else:
        await message.reply("❌ Invalid start parameter format.")

@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def addpremium(client, message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("Usage: /addpremium <user_id> <7day|1month|3month>")
        return

    user_id = int(parts[1])
    plan = parts[2].lower()
    days_map = {"7day": 7, "1month": 30, "3month": 90}
    days = days_map.get(plan)
    if not days:
        await message.reply("Invalid duration. Use 7day, 1month, or 3month.")
        return
    expire = datetime.utcnow() + timedelta(days=days)
    await db.set_premium(user_id, expire)
    await message.reply(f"✅ Premium granted to user {user_id} for {plan}.")

@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def removepremium(client, message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Usage: /removepremium <user_id>")
        return

    user_id = int(parts[1])
    await db.remove_premium(user_id)
    await message.reply(f"✅ Premium removed from user {user_id}.")
        
