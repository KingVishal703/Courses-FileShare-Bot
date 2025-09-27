import os
import re
import json
import base64
import logging
import random
import asyncio
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, CallbackQuery
from pyrogram.errors import FloodWait, UserNotParticipant, ChannelInvalid, UsernameInvalid, UsernameNotModified

from plugins.dbusers import db
from plugins.users_api import get_user, get_short_link, update_user_info
from plugins.database import get_file_details
from config import (
    ADMINS, LOG_CHANNEL, WEBSITE_URL, WEBSITE_URL_MODE,
    VERIFY_TUTORIAL, PICS, AUTO_DELETE_MODE, AUTO_DELETE_TIME, CUSTOM_FILE_CAPTION,
    STREAM_MODE, VERIFY_MODE, AUTH_CHANNEL
)
from Script import script

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BATCH_FILES = {}

def get_premium_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL)],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")]
    ])

def get_size(size):
    """Convert bytes into human-readable format"""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    i = 0
    size = float(size)
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

async def is_subscribed(bot, query, channel_list):
    btn = []
    for ch_id in channel_list:
        chat = await bot.get_chat(int(ch_id))
        try:
            await bot.get_chat_member(ch_id, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
        except Exception:
            continue
    return btn

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    user_id = message.from_user.id
    username = (await client.get_me()).username

    # Add new user
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(user_id, message.from_user.mention))

    # Force subscription check
    if AUTH_CHANNEL:
        try:
            btn = await is_subscribed(client, message, AUTH_CHANNEL)
            if btn:
                param = message.command[1] if len(message.command) > 1 else "true"
                btn.append([InlineKeyboardButton("♻️ Try Again ♻️", url=f"https://t.me/{username}?start={param}")])
                await message.reply_text(
                    f"<b>👋 Hello {message.from_user.mention}, कृपया नीचे दिए गये चैनल को join करें और Try again बटन पर क्लिक करें।</b>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
        except Exception as e:
            logger.warning(e)

    # Simple start message
    if len(message.command) == 1:
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
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, username),
            reply_markup=reply_markup
        )
        return

    # Handle start parameter
    start_param = message.command[1]
    padding = '=' * (-len(start_param) % 4)
    try:
        decoded = base64.urlsafe_b64decode(start_param + padding).decode("utf-8")
    except Exception:
        await message.reply("Invalid start parameter.")
        return

    user = await get_user(user_id)
    is_premium = await db.check_premium(user_id)

    # Single file link
    if decoded.startswith("file_") or decoded.startswith("filep_"):
        file_id = decoded.split("_", 1)[1]
        files = await get_file_details(file_id)

        if files:
            files = files[0]
            title = files.file_name
            size = get_size(files.file_size)
            caption = CUSTOM_FILE_CAPTION.format(file_name=title, file_size=size, file_caption=files.caption) if CUSTOM_FILE_CAPTION else files.caption

            if is_premium:
                await client.send_document(user_id, files.file_id, caption=caption)
            else:
                share_link = (f"{WEBSITE_URL}?Tech_VJ={start_param}" if WEBSITE_URL_MODE
                              else f"https://t.me/{username}?start={start_param}")
                short_link = await get_short_link(user, share_link) if user.get("base_site") and user.get("shortener_api") else share_link
                await message.reply(f"Your shortlink:\n{short_link}", reply_markup=get_premium_buttons())
        else:
            await message.reply("File not found.")

    # Batch file link
    elif decoded.startswith("BATCH-"):
        file_id = decoded.split("-", 1)[1]
        await message.reply("Batch links are not supported yet.")  # You can implement batch logic here

@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium(client, message):
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Use /addpremium <user_id> <7day|1month|3month>")

    user_id = int(parts[1])
    plan = parts[2].lower()
    days = {"7day": 7, "1month": 30, "3month": 90}.get(plan)
    if not days:
        return await message.reply("Invalid duration. Use 7day, 1month or 3month.")

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
    await message.reply(f"Removed premium from user {user_id}.")

# Base site / Shortener API commands
@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m):
    user_id = m.from_user.id
    cmd = m.command
    if len(cmd) == 1:
        return await m.reply("Usage: /base_site <domain> or /base_site None")

    base_site = cmd[1].strip()
    await update_user_info(user_id, {"base_site": None if base_site.lower() == "none" else base_site})
    await m.reply(f"Base site updated to: {base_site}")

@Client.on_message(filters.command("api") & filters.private)
async def shortener_api_handler(client, m):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command

    if len(cmd) == 1:
        await m.reply(script.SHORTENER_API_MESSAGE.format(base_site=user["base_site"], shortener_api=user["shortener_api"]))
    else:
        api = cmd[1].strip()
        await update_user_info(user_id, {"shortener_api": api})
        await m.reply(f"Shortener API updated to: {api}")

# Callback query handler
@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data in ["start", "about", "clone"]:
        buttons = []
        if query.data == "about":
            buttons = [[InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
                        InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
            await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
            await query.message.edit_text(script.ABOUT_TXT.format((await client.get_me()).mention), reply_markup=InlineKeyboardMarkup(buttons))
        elif query.data == "start":
            buttons = [
                [InlineKeyboardButton('🔍 Support Group', url='https://t.me/'),
                 InlineKeyboardButton('🤖 Update Channel', url='https://t.me/+K57B1ypoxfM2NmE9')],
                [InlineKeyboardButton('💁‍♀️ Info', callback_data='help'),
                 InlineKeyboardButton('😊 About', callback_data='about')]
            ]
            await client.edit_message_media(query.message.chat.id, query.message.id, InputMediaPhoto(random.choice(PICS)))
            await query.message.edit_text(script.START_TXT.format(query.from_user.mention, (await client.get_me()).username),
                                          reply_markup=InlineKeyboardMarkup(buttons))
        elif query.data == "clone":
            buttons = [[InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
                        InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
            await client.edit_message_media(query.message.chat.id
