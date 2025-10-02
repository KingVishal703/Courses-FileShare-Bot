import re
import os
import json
import base64
import logging
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE
from plugins.database import unpack_new_file_id, save_file
from plugins.users_api import get_user
from plugins.shortlink import make_shortlink
from plugins.premium import is_premium

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def incoming_gen_link(bot, message):
    try:
        await message.reply("📥 Step 1: File received...")

        username = (await bot.get_me()).username
        file_type = message.media
        media_file = getattr(message, file_type.value)

        await message.reply(f"📂 Step 2: Got file_type={file_type}, file_id={media_file.file_id}")

        file_id, file_ref = unpack_new_file_id(media_file.file_id)
        await message.reply(f"🗂️ Step 3: Decoded file_id={file_id}, file_ref={file_ref}")

        if not file_id:
            return await message.reply("❌ Step 3 failed: Could not decode file_id")

        await save_file(
            file_id=file_id,
            file_ref=file_ref,
            file_name=getattr(media_file, "file_name", "Unknown"),
            file_size=getattr(media_file, "file_size", 0),
            file_type=file_type.value,
            mime_type=getattr(media_file, "mime_type", None),
            caption=message.caption,
            chat_id=message.chat.id,
            msg_id=message.id
        )
        await message.reply("💾 Step 4: File saved to DB")

        string = 'file_' + file_id
        outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        share_link = f"https://t.me/{username}?start={outstr}"
        await message.reply(f"🔗 Step 5: Generated share link: {share_link}")

        user_id = message.from_user.id
        premium_user = await is_premium(user_id)
        await message.reply(f"👤 Step 6: Premium={premium_user}")

        if premium_user:
            reply_text = f"💎 Premium User\n\n🔗 Direct Link:\n{share_link}"
        else:
            short_link = await make_shortlink(share_link)
            await message.reply(f"🔗 Step 7: Shortlink={short_link}")
            reply_text = f"⭕ Your Link:\n\n🖇️ {short_link}"

        await message.reply("✅ Step 8: Final Reply Sent")
        await message.reply(reply_text)

    except Exception as e:
        await message.reply(f"❌ ERROR: {e}")


@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    username = (await bot.get_me()).username
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')

    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("**Reply to a supported media**")

    media_file = getattr(replied, file_type.value)
    file_id, file_ref = unpack_new_file_id(media_file.file_id)

    # Save in DB
    await save_file(
        file_id=file_id,
        file_ref=file_ref,
        file_name=getattr(media_file, "file_name", "Unknown"),
        file_size=getattr(media_file, "file_size", 0),
        file_type=file_type.value,
        mime_type=getattr(media_file, "mime_type", None),
        caption=replied.caption,
        chat_id=replied.chat.id,
        msg_id=replied.id
    )

    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    # ✅ Premium check
    user_id = message.from_user.id
    premium_user = await is_premium(user_id)

    if premium_user:
        reply_text = f"<b>💎 Premium User Detected!</b>\n\nHere is your direct link:\n\n🔗 {share_link}"
    else:
        short_link = await make_shortlink(share_link)
        reply_text = f"<b>⭕ Here is your link:</b>\n\n🖇️ Short Link: {short_link}"

    await message.reply(reply_text)



