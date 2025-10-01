# Credit: @VJ_Botz | YouTube: @Tech_VJ | Telegram: @KingVJ01

import re
import os
import json
import base64
import logging

from pyrogram import filters, Client, enums
from pyrogram.errors import ChannelInvalid, UsernameInvalid, UsernameNotModified

from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE
from plugins.database import unpack_new_file_id
from plugins.users_api import get_user, get_short_link

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


async def store_file_to_log_channel(bot, message):
    """Upload the incoming file to LOG_CHANNEL and return new file_id"""
    media_attr = getattr(message, message.media.value)
    caption = getattr(message, "caption", "")
    try:
        if message.media == enums.MessageMediaType.DOCUMENT:
            post = await bot.send_document(LOG_CHANNEL, media_attr.file_id, caption=caption)
        elif message.media == enums.MessageMediaType.VIDEO:
            post = await bot.send_video(LOG_CHANNEL, media_attr.file_id, caption=caption)
        elif message.media == enums.MessageMediaType.AUDIO:
            post = await bot.send_audio(LOG_CHANNEL, media_attr.file_id, caption=caption)
        else:
            return None
        return post.document.file_id if post.document else (post.video.file_id if post.video else post.audio.file_id)
    except Exception as e:
        logger.error(f"Error storing file to log channel: {e}")
        return None


@Client.on_message((filters.document | filters.video | filters.audio) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    try:
        username = (await bot.get_me()).username
        # Upload file to log channel
        log_file_id = await store_file_to_log_channel(bot, message)
        if not log_file_id:
            return await message.reply("❌ Failed to store file in channel.")

        # Encode link
        file_id, _ = unpack_new_file_id(log_file_id)
        string = f"file_{file_id}"
        outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        user_id = message.from_user.id
        user = await get_user(user_id)

        if WEBSITE_URL_MODE:
            share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
        else:
            share_link = f"https://t.me/{username}?start={outstr}"

        if user.get("base_site") and user.get("shortener_api"):
            short_link = await get_short_link(user, share_link)
            await message.reply(f"<b>⭕ Your Link:\n\n🖇️ Short Link: {short_link}</b>")
        else:
            await message.reply(f"<b>⭕ Your Link:\n\n🔗 Original Link: {share_link}</b>")

    except Exception as e:
        logger.error(f"Error in incoming_gen_link: {e}")
        await message.reply(f"❌ Failed to generate link: {e}")


@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    try:
        username = (await bot.get_me()).username
        replied = message.reply_to_message
        if not replied:
            return await message.reply('Reply to a message to get a shareable link.')

        if replied.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
            return await message.reply("**Reply to a supported media**")

        # Upload replied file to log channel
        log_file_id = await store_file_to_log_channel(bot, replied)
        if not log_file_id:
            return await message.reply("❌ Failed to store file in channel.")

        # Encode link
        file_id, _ = unpack_new_file_id(log_file_id)
        string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
        string += file_id
        outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        user_id = message.from_user.id
        user = await get_user(user_id)

        if WEBSITE_URL_MODE:
            share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
        else:
            share_link = f"https://t.me/{username}?start={outstr}"

        if user.get("base_site") and user.get("shortener_api"):
            short_link = await get_short_link(user, share_link)
            await message.reply(f"<b>⭕ Your Link:\n\n🖇️ Short Link: {short_link}</b>")
        else:
            await message.reply(f"<b>⭕ Your Link:\n\n🔗 Original Link: {share_link}</b>")

    except Exception as e:
        logger.error(f"Error in gen_link_s: {e}")
        await message.reply(f"❌ Failed to generate link: {e}")
