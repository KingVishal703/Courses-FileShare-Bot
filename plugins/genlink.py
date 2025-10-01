# plugins/genlink.py
import re
import os
import json
import base64
import logging
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE
from plugins.database import unpack_new_file_id
from plugins.users_api import get_user, get_short_link

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------
# Helper: check if user allowed
# -----------------------------
async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


# -----------------------------
# Single media incoming
# -----------------------------
@Client.on_message((filters.document | filters.video | filters.audio) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    user_id = message.from_user.id
    username = (await bot.get_me()).username
    user = await get_user(user_id)

    file_obj = message.document or message.video or message.audio
    if not file_obj:
        return await message.reply("⚠️ Unsupported media type.")

    file_id, _ = unpack_new_file_id(file_obj.file_id)
    string = f"file_{file_id}"
    outstr = base64.urlsafe_b64encode(string.encode()).decode().strip("=")

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    if user.get("base_site") and user.get("shortener_api"):
        short_link = await get_short_link(user, share_link)
        await message.reply(f"<b>⭕ Here is your link:\n🖇️ Short link: {short_link}</b>")
    else:
        await message.reply(f"<b>⭕ Here is your link:\n🔗 Original link: {share_link}</b>")


# -----------------------------
# /link or /plink command
# -----------------------------
@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply("Reply to a message to get a shareable link.")

    file_obj = replied.document or replied.video or replied.audio
    if not file_obj:
        return await message.reply("**Reply to a supported media (video, audio, document)**")

    if getattr(replied, "has_protected_content", False) and message.from_user.id not in ADMINS:
        return await message.reply("⚠️ This media is protected.")

    file_id, _ = unpack_new_file_id(file_obj.file_id)
    prefix = "filep_" if message.text.lower().strip() == "/plink" else "file_"
    string = f"{prefix}{file_id}"
    outstr = base64.urlsafe_b64encode(string.encode()).decode().strip("=")

    user_id = message.from_user.id
    username = (await bot.get_me()).username
    user = await get_user(user_id)

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ={outstr}"
    else:
        share_link = f"https://t.me/{username}?start={outstr}"

    if user.get("base_site") and user.get("shortener_api"):
        short_link = await get_short_link(user, share_link)
        await message.reply(f"<b>⭕ Here is your link:\n🖇️ Short link: {short_link}</b>")
    else:
        await message.reply(f"<b>⭕ Here is your link:\n🔗 Original link: {share_link}</b>")


# -----------------------------
# /batch or /pbatch command
# -----------------------------
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    username = (await bot.get_me()).username
    if " " not in message.text:
        return await message.reply("Use correct format:\nExample: /batch https://t.me/... https://t.me/...")

    links = message.text.strip().split()
    if len(links) != 3:
        return await message.reply("Use correct format:\nExample: /batch https://t.me/... https://t.me/...")

    cmd, first, last = links
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")

    # First link
    match = regex.match(first)
    if not match:
        return await message.reply("Invalid first link")
    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int("-100" + f_chat_id)

    # Last link
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
        return await message.reply("Private channel/group? Make me admin.")
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("Invalid chat link.")
    except Exception as e:
        return await message.reply(f"Error: {e}")

    sts = await message.reply("**Generating links... This may take time depending on number of messages**")

    outlist = []
    og_msg = 0

    # Proper iter_messages usage
    async for msg in bot.iter_messages(chat_id, offset_id=l_msg_id-1, reverse=True):
        if msg.id < f_msg_id:
            break
        if msg.empty or msg.service:
            continue
        if not msg.media:
            continue
        try:
            file_obj = msg.document or msg.video or msg.audio
            if not file_obj:
                continue
            caption = msg.caption or ""
            file_data = {
                "file_id": file_obj.file_id,
                "caption": caption,
                "title": getattr(file_obj, "file_name", ""),
                "size": getattr(file_obj, "file_size", 0),
                "protect": cmd.lower().strip() == "/pbatch",
            }
            outlist.append(file_data)
            og_msg += 1
        except:
            continue

    # Save temporary JSON
    temp_file = f"batchmode_{message.from_user.id}.json"
    with open(temp_file, "w+") as out:
        json.dump(outlist, out)

    # Send to log channel
    post = await bot.send_document(LOG_CHANNEL, temp_file, file_name="Batch.json", caption="⚠️ Generated for filestore.")
    os.remove(temp_file)

    file_id, _ = unpack_new_file_id(post.document.file_id)
    user_id = message.from_user.id
    user = await get_user(user_id)

    if WEBSITE_URL_MODE:
        share_link = f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}"
    else:
        share_link = f"https://t.me/{username}?start=BATCH-{file_id}"

    if user.get("base_site") and user.get("shortener_api"):
        short_link = await get_short_link(user, share_link)
        await sts.edit(f"<b>⭕ Here is your batch link:\nContains `{og_msg}` files\n🖇️ Short link: {short_link}</b>")
    else:
        await sts.edit(f"<b>⭕ Here is your batch link:\nContains `{og_msg}` files\n🔗 Original link: {share_link}</b>")
