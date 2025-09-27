import re
import os
import json
import base64
import logging
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE
from plugins.database import unpack_new_file_id
from plugins.users_api import get_user, get_short_link
from plugins.dbusers import db
from plugins.commands import get_premium_buttons
from datetime import datetime

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
    username = (await bot.get_me()).username
    file_type = message.media
    file_id, ref = unpack_new_file_id((getattr(message, file_type.value)).file_id)
    string = 'file_' + file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user_id = message.from_user.id
    user = await get_user(user_id)

    # DB premium status check
    is_premium = await db.check_premium(user_id)

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    if is_premium:
        await message.reply(
            f"<b>⭕ Your premium access link:\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
            reply_markup=get_premium_buttons()
        )
    else:
        if user["base_site"] and user["shortener_api"]:
            short_link = await get_short_link(user, share_link)
            await message.reply(
                f"<b>⭕ Here is your link:\n\n🖇️ SHORT LINK :- {short_link}</b>",
                reply_markup=get_premium_buttons()
            )
        else:
            await message.reply(
                f"<b>⭕ Here is your link:\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
                reply_markup=get_premium_buttons()
            )

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    username = (await bot.get_me()).username
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')

    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("Reply to a supported media")
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")

    file_id, ref = unpack_new_file_id((getattr(replied, file_type.value)).file_id)
    string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
    user_id = message.from_user.id
    user = await get_user(user_id)

    is_premium = await db.check_premium(user_id)

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    if is_premium:
        await message.reply(
            f"<b>⭕ Your premium access link:\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
            reply_markup=get_premium_buttons()
        )
    else:
        if user["base_site"] and user["shortener_api"]:
            short_link = await get_short_link(user, share_link)
            await message.reply(
                f"<b>⭕ Here is your link:\n\n🖇️ SHORT LINK :- {short_link}</b>",
                reply_markup=get_premium_buttons()
            )
        else:
            await message.reply(
                f"<b>⭕ Here is your link:\n\n🔗 ORIGINAL LINK :- {share_link}</b>",
                reply_markup=get_premium_buttons()
            )

@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    username = (await bot.get_me()).username
    if " " not in message.text:
        return await message.reply("Use correct format.\nExample /batch https://t.me// https://t.me/.")
    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply("Use correct format.\nExample /batch https://t.me/ https://t.me/.")
    cmd, first, last = links
    regex = re.compile("(https://)?(t.me/|telegram.me/|telegram.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    match = regex.match(first)
    if not match:
        return await message.reply('Invalid link')
    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int(("-100" + f_chat_id))

    match = regex.match(last)
    if not match:
        return await message.reply('Invalid link')
    l_chat_id = match.group(4)
    l_msg_id = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id = int(("-100" + l_chat_id))

    if f_chat_id != l_chat_id:
        return await message.reply("Chat ids not matched.")
    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    sts = await message.reply("ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ ғᴏʀ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ.\nᴛʜɪs ᴍᴀʏ ᴛᴀᴋᴇ ᴛɪᴍᴇ ᴅᴇᴘᴇɴᴅɪɴɢ ᴜᴘᴏɴ ɴᴜᴍʙᴇʀ ᴏғ ᴍᴇssᴀɢᴇs")

    FRMT = "ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ...\nᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs: {total}\nᴅᴏɴᴇ: {current}\nʀᴇᴍᴀɪɴɪɴɢ: {rem}\nsᴛᴀᴛᴜs: {sts}"

    outlist = []

    og_msg = 0
    tot = 0
    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service:
            continue
        if not msg.media:
            continue
        try:
            file_type = msg.media
            file = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
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
                await sts.edit(FRMT.format(total=l_msg_id-f_msg_id, current=tot, rem=((l_msg_id-f_msg_id) - tot), sts="Saving Messages"))
            except:
                pass

    with open(f"batchmode_{message.from_user.id}.json", "w+") as out:
        json.dump(outlist, out)
    post = await bot.send_document(LOG_CHANNEL, f"batchmode_{message.from_user.id}.json", file_name="Batch.json", caption="⚠️Generated for filestore.")
    os.remove(f"batchmode_{message.from_user.id}.json")
    file_id, ref = unpack_new_file_id(post.document.file_id)
    user_id = message.from_user.id
    user = await get_user(user_id)
    is_premium = await db.check_premium(user_id)
    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}"
    else:
        share_link = f"https://t.me/{username}?start=BATCH-{file_id}"
    if is_premium:
        await sts.edit(f"<b>⭕ Here is your premium batch link:\n\nContains {og_msg} files.\n\n🔗 ORIGINAL LINK :- {share_link}</b>", reply_markup=get_premium_buttons())
    else:
        if user["base_site"] and user["shortener_api"]:
            short_link = await get_short_link(user, share_link)
            await sts.edit(f"<b>⭕ Here is your link:\n\nContains {og_msg} files.\n\n🖇️ SHORT LINK :- {short_link}</b>", reply_markup=get_premium_buttons())
        else:
            await sts.edit(f"<b>⭕ Here is your link:\n\nContains {og_msg} files.\n\n🔗 ORIGINAL LINK :- {share_link}</b>", reply_markup=get_premium_buttons())
    
