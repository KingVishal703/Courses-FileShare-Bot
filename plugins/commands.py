import os
import logging
import random
import asyncio
import base64
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from validators import domain
from Script import script
from plugins.dbusers import db
from plugins.users_api import get_user, update_user_info, get_short_link
from plugins.database import get_file_details
from pyrogram import Client, filters, enums
from pyrogram.errors import *
from pyrogram.types import *
from utils import verify_user, check_token, check_verification, get_token
from config import *
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)
BATCH_FILES = {}

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

async def is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
        except Exception:
            pass
    return btn

def get_premium_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL)],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")]
    ])

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    user_id = message.from_user.id
    username = (await client.get_me()).username

    # Force join channels
    if AUTH_CHANNEL:
        try:
            btn = await is_subscribed(client, message, AUTH_CHANNEL)
            if btn:
                if len(message.command) == 2:
                    btn.append([InlineKeyboardButton("♻️ Try Again ♻️", url=f"https://t.me/{username}?start={message.command[1]}")])
                else:
                    btn.append([InlineKeyboardButton("♻️ Try Again ♻️", url=f"https://t.me/{username}?start=true")])
                await message.reply_text(
                    text=f"<b>👋 Hello {message.from_user.mention}, कृपया नीचे दिए गए चैनल को join करें और Try again बटन पर क्लिक करें। 🙂</b>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
        except Exception as e:
            logger.warning(e)

    # Add user if not exists
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(user_id, message.from_user.mention))

    # Normal start without parameter
    if len(message.command) == 1:
        buttons = [
            [
                InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/'),
                InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/+K57B1ypoxfM2NmE9')
            ],
            [
                InlineKeyboardButton('💁‍♀️ Info', callback_data='help'),
                InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
            ]
        ]
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])

        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, me2),
            reply_markup=reply_markup
        )
        return

    # Start parameter exists
    start_param = message.command[1]
    padding = '=' * (-len(start_param) % 4)
    try:
        decoded = base64.urlsafe_b64decode(start_param + padding).decode("utf-8")
    except Exception:
        return await message.reply_text("Invalid start parameter.")

    user = await get_user(user_id)
    is_premium = await db.check_premium(user_id)

    # File handling
    if decoded.startswith("file_"):
        file_id = decoded[5:]
        if is_premium:
            file_data = await get_file_details(file_id)
            if not file_data:
                return await message.reply("File not found.")
            await client.send_document(user_id, file_data['file_id'], caption=file_data.get('caption', ''))
        else:
            share_link = f"{WEBSITE_URL}?Tech_VJ={start_param}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={start_param}"
            short_link = await get_short_link(user, share_link) if user.get("base_site") and user.get("shortener_api") else share_link
            await message.reply(f"Your short link:\n{short_link}", reply_markup=get_premium_buttons())

    # Batch handling (simplified)
    elif decoded.startswith("BATCH-"):
        batch_id = decoded[6:]
        await message.reply("Batch link handling not implemented yet.")

    # Verification / token handling (existing logic)
    elif decoded.startswith("verify-"):
        parts = decoded.split("-", 2)
        userid = parts[1]
        token = parts[2]
        if str(user_id) != str(userid):
            return await message.reply_text("<b>Invalid link or Expired link !</b>", protect_content=True)
        if await check_token(client, userid, token):
            await message.reply_text(f"<b>Hey {message.from_user.mention}, You are successfully verified !\nअब आप 24 घनटे तक सभी वीडियो देख सकते है.</b>", protect_content=True)
            await verify_user(client, userid, token)
        else:
            await message.reply_text("<b>Invalid link or Expired link Try Again !</b>", protect_content=True)

# Admin premium commands
@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium(client, message):
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Use /addpremium <user_id> <7day|1month|3month>")
    user_id = int(parts[1])
    plan = parts[2].lower()
    duration_map = {"7day":7, "1month":30, "3month":90}
    days = duration_map.get(plan)
    if not days:
        return await message.reply("Invalid plan. Choose from 7day, 1month, 3month.")
    expiry = datetime.utcnow() + timedelta(days=days)
    await db.set_premium(user_id, expiry)
    await message.reply(f"Premium granted to user {user_id} for {plan}.")

@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def remove_premium(client, message):
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply("Use /removepremium <user_id>")
    user_id = int(parts[1])
    await db.remove_premium(user_id)
    await message.reply(f"Premium removed from user {user_id}.")
