import re
import os
import json
import base64
import logging
import random
import aiohttp
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE, VERIFY_TUTORIAL, SHORTENER_APIS
from plugins.database import unpack_new_file_id
from plugins.users_api import get_user, get_short_link
from plugins.dbusers import db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_premium_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL)],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")]
    ])

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    username = (await bot.get_me()).username
    file_type = message.media
    file_id, _ = unpack_new_file_id((getattr(message, file_type.value)).file_id)
    string = 'file_' + file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")

    user_id = message.from_user.id
    user = await get_user(user_id)
    is_premium = await db.check_premium(user_id)

    share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={outstr}"

    if is_premium:
        await message.reply(
            f"<b>⭕ Your premium access link:\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
            reply_markup=get_premium_buttons()
        )
    else:
        short_link = await get_short_link(user, share_link)
        await message.reply(
            f"<b>⭕ Here is your link:\n\n🖇️ SHORT LINK :- {short_link}</b>",
            reply_markup=get_premium_buttons()
        )

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    username = (await bot.get_me()).username
    replied = message.reply_to_message
    if not replied:
        return await message.reply("Reply to a message to get a shareable link.")

    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("Reply to a supported media.")

    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")

    file_id, _ = unpack_new_file_id((getattr(replied, file_type.value)).file_id)
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")

    user_id = message.from_user.id
    user = await get_user(user_id)
    is_premium = await db.check_premium(user_id)

    share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start={outstr}"

    if is_premium:
        await message.reply(
            f"<b>⭕ Your premium access link:\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
            reply_markup=get_premium_buttons()
        )
    else:
        short_link = await get_short_link(user, share_link)
        await message.reply(
            f"<b>⭕ Here is your link:\n\n🖇️ SHORT LINK :- {short_link}</b>",
            reply_markup=get_premium_buttons()
        )

@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    username = (await bot.get_me()).username
    if " " not in message.text:
        return await message.reply("Use correct format.\nExample: /batch https://t.me/... https://t.me/...")

    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply("Use correct format.\nExample: /batch https://t.me/... https://t.me/...")

    cmd, first, last = links
    regex = re.compile(r"(https://)?(t.me/|telegram.me/|telegram.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")

    match = regex.match(first)
    if not match:
        return await message.reply("Invalid first link")

    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int("-100" + f_chat_id)

    match = regex.match(last)
    if not match:
        return await message.reply("Invalid last link")

    l_chat_id = match.group(4)
    l_msg_id = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id = int("-100" + l_chat_id)

    if f_chat_id != l_chat_id:
        return await message.reply("Chat IDs do not match.")

    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply("Private channel/group. Make me admin to index.")
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("Invalid link specified.")
    except Exception as e:
        return await message.reply(f"Error: {e}")

    sts = await message.reply("Generating batch link...\nPlease wait ⏳")

    FRMT = "Generating...\nTotal: {total}\nDone: {current}\nRemaining: {rem}\nStatus: {sts}"

    outlist, og_msg, tot = [], 0, 0

    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service or not msg.media:
            continue
        try:
            file_type = msg.media
            file = getattr(msg, file_type.value)
            caption = getattr(msg, "caption", "") or ""
            if caption:
                caption = caption.html
            if file:
                file = {
                    "file_id": file.file_id,
                    "caption": caption,
                    "title": getattr(file, "file_name", ""),
                    "size": file.file_size,
                    "protect": cmd.lower().strip() == "/pbatch",
                }
                og_msg += 1
                outlist.append(file)
        except:
            pass
        if not og_msg % 20:
            try:
                await sts.edit(FRMT.format(
                    total=l_msg_id - f_msg_id,
                    current=tot,
                    rem=(l_msg_id - f_msg_id) - tot,
                    sts="Saving Messages"
                ))
            except:
                pass

    with open(f"batchmode_{message.from_user.id}.json", "w+") as out:
        json.dump(outlist, out)

    post = await bot.send_document(LOG_CHANNEL,
                                   f"batchmode_{message.from_user.id}.json",
                                   file_name="Batch.json",
                                   caption="⚠️ Generated for filestore.")

    os.remove(f"batchmode_{message.from_user.id}.json")

    file_id, _ = unpack_new_file_id(post.document.file_id)
    user_id = message.from_user.id
    user = await get_user(user_id)
    is_premium = await db.check_premium(user_id)

    share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}" if WEBSITE_URL_MODE else f"https://t.me/{username}?start=BATCH-{file_id}"

    if is_premium:
        await sts.edit(
            f"<b>⭕ Here is your premium batch link:\n\nContains {og_msg} files.\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
            reply_markup=get_premium_buttons()
        )
    else:
        short_link = await get_short_link(user, share_link)
        await sts.edit(
            f"<b>⭕ Here is your link:\n\nContains {og_msg} files.\n\n🖇️ SHORT LINK :- {short_link}</b>",
            reply_markup=get_premium_buttons()
    )
    
