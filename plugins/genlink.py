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


@Client.on_message((filters.document | filters.video | filters.audio) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    try:
        username = (await bot.get_me()).username
        media_attr = getattr(message, message.media.value)
        file_id, _ = unpack_new_file_id(media_attr.file_id)

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

        media_attr = getattr(replied, replied.media.value)
        file_id, _ = unpack_new_file_id(media_attr.file_id)

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


@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    try:
        username = (await bot.get_me()).username
        args = message.text.strip().split(" ")
        if len(args) != 3:
            return await message.reply("Use correct format:\nExample: /batch https://t.me/... https://t.me/...")

        cmd, first, last = args
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?([\w\d_]+)/(\d+)$")

        match_first = regex.match(first)
        match_last = regex.match(last)
        if not match_first or not match_last:
            return await message.reply("Invalid link format.")

        f_chat_id, f_msg_id = match_first.group(4), int(match_first.group(5))
        l_chat_id, l_msg_id = match_last.group(4), int(match_last.group(5))

        if f_chat_id.isnumeric():
            f_chat_id = int(f"-100{f_chat_id}")
        if l_chat_id.isnumeric():
            l_chat_id = int(f"-100{l_chat_id}")

        if f_chat_id != l_chat_id:
            return await message.reply("Chat IDs do not match.")

        chat_id = await bot.get_chat(f_chat_id)
        sts = await message.reply("**Generating links... This may take time depending on number of messages.**")
        outlist = []
        count = 0

        async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
            if msg.empty or msg.service or not msg.media:
                continue
            try:
                media_attr = getattr(msg, msg.media.value)
                file_info = {
                    "file_id": media_attr.file_id,
                    "caption": getattr(msg, 'caption', '') or '',
                    "title": getattr(media_attr, "file_name", ""),
                    "size": getattr(media_attr, "file_size", 0),
                    "protect": cmd.lower().strip() == "/pbatch"
                }
                outlist.append(file_info)
                count += 1
                if count % 20 == 0:
                    await sts.edit(f"Processed {count} messages...")
            except:
                continue

        batch_file = f"batchmode_{message.from_user.id}.json"
        with open(batch_file, "w") as f:
            json.dump(outlist, f)

        post = await bot.send_document(LOG_CHANNEL, batch_file, file_name="Batch.json", caption="⚠️ Generated for filestore.")
        os.remove(batch_file)
        file_id, _ = unpack_new_file_id(post.document.file_id)

        user_id = message.from_user.id
        user = await get_user(user_id)
        if WEBSITE_URL_MODE:
            share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}"
        else:
            share_link = f"https://t.me/{username}?start=BATCH-{file_id}"

        if user.get("base_site") and user.get("shortener_api"):
            short_link = await get_short_link(user, share_link)
            await sts.edit(f"<b>⭕ Here is your link:\n\nContains `{count}` files\n🖇️ Short Link: {short_link}</b>")
        else:
            await sts.edit(f"<b>⭕ Here is your link:\n\nContains `{count}` files\n🔗 Original Link: {share_link}</b>")

    except Exception as e:
        logger.error(f"Error in gen_link_batch: {e}")
        await message.reply(f"❌ Failed to generate batch link: {e}")
