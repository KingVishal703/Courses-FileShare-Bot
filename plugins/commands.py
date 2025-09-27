import os
import logging
import random
import asyncio
import base64
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from validators import domain
from pyrogram import Client, filters, enums
from pyrogram.errors import *
from pyrogram.types import *
from plugins.dbusers import db
from plugins.users_api import get_user, update_user_info, get_short_link
from plugins.database import get_file_details
from Script import script
from utils import verify_user, check_token, check_verification, get_token
from config import *
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)
BATCH_FILES = {}

# --------------------- Helper Functions ---------------------
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

async def is_subscribed(bot, query, channels):
    btn = []
    for ch in channels:
        chat = await bot.get_chat(int(ch))
        try:
            await bot.get_chat_member(ch, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
    return btn

def get_premium_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL)],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")]
    ])

# --------------------- Start Command ---------------------
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    user_id = message.from_user.id
    username = (await client.get_me()).username

    # Add user to DB if not exists
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(user_id, message.from_user.mention))

    # Check subscription if enabled
    if AUTH_CHANNEL:
        try:
            btn = await is_subscribed(client, message, AUTH_CHANNEL)
            if btn:
                retry_btn = [InlineKeyboardButton("♻️ Try Again ♻️", url=f"https://t.me/{username}?start=true")]
                btn.append(retry_btn)
                await message.reply_text(
                    text=f"<b>👋 Hello {message.from_user.mention}, कृपया नीचे दिए गए चैनल को join करें और Try again बटन पर क्लिक करें।</b>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
        except Exception as e:
            print(e)

    # If start has parameter
    if len(message.command) > 1:
        start_arg = message.command[1]
        try:
            padding = '=' * (-len(start_arg) % 4)
            decoded_bytes = base64.urlsafe_b64decode(start_arg + padding)
            decoded_str = decoded_bytes.decode('ascii')
        except:
            await message.reply("Invalid start parameter.")
            return

        # Premium file handling
        if decoded_str.startswith("file_"):
            file_id = decoded_str[5:]
            is_premium = await db.check_premium(user_id)

            if is_premium:
                files_ = await get_file_details(file_id)
                if files_:
                    files = files_[0]
                    f_caption = files.caption or files.file_name
                    await client.send_cached_media(user_id, file_id=files.file_id, caption=f_caption)
                else:
                    await message.reply("File not found.")
            else:
                user = await get_user(user_id)
                share_link = f"{WEBSITE_URL}?Tech_VJ={start_arg}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={start_arg}"
                short_link = await get_short_link(user, share_link) if user["base_site"] and user["shortener_api"] else share_link
                await message.reply(f"Your download link:\n{short_link}", reply_markup=get_premium_buttons())
            return

    # Default start message
    buttons = [
        [
            InlineKeyboardButton('🔍 Support Group', url='https://t.me/'),
            InlineKeyboardButton('🤖 Update Channel', url='https://t.me/+K57B1ypoxfM2NmE9')
        ],
        [
            InlineKeyboardButton('💁‍♀️ Info', callback_data='help'),
            InlineKeyboardButton('😊 About', callback_data='about')
        ]
    ]
    if CLONE_MODE:
        buttons.append([InlineKeyboardButton('🤖 Create Your Own Clone Bot', callback_data='clone')])

    reply_markup = InlineKeyboardMarkup(buttons)
    me2 = (await client.get_me()).mention
    await message.reply_photo(
        photo=random.choice(PICS),
        caption=script.START_TXT.format(message.from_user.mention, me2),
        reply_markup=reply_markup
    )

# --------------------- Premium Management Commands ---------------------
@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def handle_addpremium(client, message):
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Usage: /addpremium <user_id> <7day|1month|3month>")

    try:
        user_id = int(parts[1])
        duration_map = {'7day': 7, '1month': 30, '3month': 90}
        days = duration_map.get(parts[2].lower())
        if not days:
            return await message.reply("Invalid duration. Use 7day, 1month, or 3month.")
        expiry = datetime.now() + timedelta(days=days)
        await db.set_premium(user_id, expiry)
        await message.reply(f"User {user_id} given premium for {parts[2]}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def handle_removepremium(client, message):
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply("Usage: /removepremium <user_id>")
    try:
        user_id = int(parts[1])
        await db.remove_premium(user_id)
        await message.reply(f"Premium removed for user {user_id}.")
    except Exception as e:
        await message.reply(f"Error: {e}")
