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

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import urlparse, parse_qs
import base64

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    user_id = message.from_user.id
    username = (await client.get_me()).username

    # Agar user sirf /start bhej raha hai
    if len(message.command) == 1:
        if not await db.is_user_exist(user_id):
            await db.add_user(user_id, message.from_user.first_name)
        return await message.reply(
            "👋 Welcome! Send me a file to start."
        )

    start_param = message.command[1]

    # ---------------- Double Decode Logic ---------------- #
    try:
        padding = '=' * (-len(start_param) % 4)
        first_decode = base64.urlsafe_b64decode(start_param + padding).decode()

        # Agar first decode me shortlink hai, toh usse dobara decode karke asli file id nikalna
        if first_decode.startswith("http"):
            parsed = urlparse(first_decode)
            params = parse_qs(parsed.query)
            start_param_2 = params.get('start', [None])[0]
            if not start_param_2:
                return await message.reply("❌ Invalid start parameter in shortlink.")
            start_param = start_param_2
            padding = '=' * (-len(start_param) % 4)

        decoded = base64.urlsafe_b64decode(start_param + padding).decode()
    except Exception:
        return await message.reply("❌ Invalid start parameter.")

    # ---------------- Handle decoded parameter ---------------- #
    if decoded.startswith("file_") or decoded.startswith("filep_"):
        is_protect = decoded.startswith("filep_")
        file_id = decoded.split("_", 1)[1]
        is_premium = await db.check_premium(user_id)

        if is_premium:
            # Premium users ko direct file bhejna
            file_data = await get_file_details(file_id)
            if not file_data:
                return await message.reply("❌ File not found.")
            await client.send_document(
                chat_id=user_id,
                document=file_data["file_id"],
                caption=file_data.get("caption", ""),
                protect_content=is_protect
            )
        else:
            # Non-premium users ke liye shortlink generate
            user = await get_user(user_id)
            share_link = f"https://t.me/{username}?start={start_param}"
            if user.get("base_site") and user.get("shortener_api"):
                short_link = await get_short_link(user, share_link)
            else:
                short_link = share_link
            await message.reply(f"🔗 Your share/short link:\n{short_link}")

    else:
        return await message.reply("❌ Invalid start parameter format.")

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

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data in ["start", "about", "clone"]:
        buttons = []
        if query.data == "about":
            buttons = [[InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
                        InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
            await client.edit_message_media(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                media=InputMediaPhoto(random.choice(PICS))
            )
            await query.message.edit_text(
                script.ABOUT_TXT.format((await client.get_me()).mention),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif query.data == "start":
            buttons = [
                [InlineKeyboardButton('🔍 Support Group', url='https://t.me/'),
                 InlineKeyboardButton('🤖 Update Channel', url='https://t.me/+K57B1ypoxfM2NmE9')],
                [InlineKeyboardButton('💁‍♀️ Info', callback_data='help'),
                 InlineKeyboardButton('😊 About', callback_data='about')]
            ]
            await client.edit_message_media(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                media=InputMediaPhoto(random.choice(PICS))
            )
            await query.message.edit_text(
                script.START_TXT.format(query.from_user.mention, (await client.get_me()).username),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif query.data == "clone":
            buttons = [[InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
                        InlineKeyboardButton('🔒 Close', callback_data='close_data')]]
            await client.edit_message_media(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                media=InputMediaPhoto(random.choice(PICS))
            )
            await query.message.edit_text(
                "Clone feature is under development.",
                reply_markup=InlineKeyboardMarkup(buttons)
)
