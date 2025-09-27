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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


# ------------------ Double Encode Helper ------------------ #
async def double_encode_link(file_id, client, user_is_premium, user):
    raw_string = f"file_{file_id}"
    encoded = base64.urlsafe_b64encode(raw_string.encode()).decode().strip("=")
    bot_username = (await client.get_me()).username

    start_link = f"https://t.me/{bot_username}?start={encoded}"

    if user_is_premium:
        return start_link

    # Non-premium users ke liye shortlink
    short_link = await get_short_link(user, start_link)
    double_encoded = base64.urlsafe_b64encode(short_link.encode()).decode().strip("=")
    final_link = f"https://t.me/{bot_username}?start={double_encoded}"
    return final_link
# --------------------------------------------------------- #


@Client.on_message((filters.document | filters.video | filters.audio) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    file_type = message.media
    file_id, ref = unpack_new_file_id(getattr(message, file_type.value).file_id)
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_is_premium = user.get("is_premium", False)  # User premium status

    final_link = await double_encode_link(file_id, bot, user_is_premium, user)
    await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🔗 ᴏʀɪɢɪɴᴀʟ/ᴅᴏᴜʙʟᴇ ʟɪɴᴋ :- {final_link}</b>")


@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')

    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
        return await message.reply("**ʀᴇᴘʟʏ ᴛᴏ ᴀ sᴜᴘᴘᴏʀᴛᴇᴅ ᴍᴇᴅɪᴀ**")
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")

    file_id, ref = unpack_new_file_id(getattr(replied, file_type.value).file_id)
    user_id = message.from_user.id
    user = await get_user(user_id)
    user_is_premium = user.get("is_premium", False)

    final_link = await double_encode_link(file_id, bot, user_is_premium, user)
    await message.reply(f"<b>⭕ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ:\n\n🔗 ᴏʀɪɢɪɴᴀʟ/ᴅᴏᴜʙʟᴇ ʟɪɴᴋ :- {final_link}</b>")
    
# ---------------- Batch Link Generation ----------------
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    username = (await bot.get_me()).username
    parts = message.text.strip().split(" ")
    if len(parts) != 3:
        return await message.reply("Use correct format:\nExample /batch https://t.me/... https://t.me/...")
    
    cmd, first, last = parts
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    
    match_first = regex.match(first)
    match_last = regex.match(last)
    if not match_first or not match_last:
        return await message.reply('Invalid link format.')
    
    f_chat_id, f_msg_id = match_first.group(4), int(match_first.group(5))
    l_chat_id, l_msg_id = match_last.group(4), int(match_last.group(5))
    if f_chat_id.isnumeric(): f_chat_id = int("-100" + f_chat_id)
    if l_chat_id.isnumeric(): l_chat_id = int("-100" + l_chat_id)
    if f_chat_id != l_chat_id:
        return await message.reply("Chat IDs do not match.")

    try:
        await bot.get_chat(f_chat_id)
    except ChannelInvalid:
        return await message.reply('Private channel/group. Make me admin there.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid link.')
    except Exception as e:
        return await message.reply(f'Error: {e}')

    sts = await message.reply("**Generating links... This may take time depending on number of messages.**")
    FRMT = "**Processing...**\nTotal: {total}\nDone: {current}\nRemaining: {rem}\nStatus: {sts}"
    outlist, og_msg, tot = [], 0, 0

    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service or not msg.media:
            continue
        try:
            file_type = msg.media
            file = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
            if caption: caption = caption.html
            if file:
                outlist.append({
                    "file_id": file.file_id,
                    "caption": caption,
                    "title": getattr(file, "file_name", ""),
                    "size": file.file_size,
                    "protect": cmd.lower().strip() == "/pbatch",
                })
                og_msg += 1
        except:
            pass

        if not og_msg % 20:
            try:
                await sts.edit(FRMT.format(total=l_msg_id-f_msg_id, current=tot, rem=(l_msg_id-f_msg_id-tot), sts="Saving"))
            except:
                pass

    # Save batch file and send to log channel
    batch_file = f"batchmode_{message.from_user.id}.json"
    with open(batch_file, "w+") as out:
        json.dump(outlist, out)
    post = await bot.send_document(LOG_CHANNEL, batch_file, file_name="Batch.json", caption="⚠️Generated for filestore.")
    os.remove(batch_file)

    file_id, _ = unpack_new_file_id(post.document.file_id)
    user = await get_user(message.from_user.id)
    is_premium = await db.check_premium(message.from_user.id)

    share_link = (f"{WEBSITE_URL}?Tech_VJ=BATCH-{file_id}" if WEBSITE_URL_MODE 
                  else f"https://t.me/{username}?start=BATCH-{file_id}")

    if is_premium:
        await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs your premium batch link containing `{og_msg}` files:\n{share_link}</b>", reply_markup=get_premium_buttons())
    elif user["base_site"] and user["shortener_api"]:
        short_link = await get_short_link(user, share_link)
        await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs your batch shortlink containing `{og_msg}` files:\n{short_link}</b>", reply_markup=get_premium_buttons())
    else:
        await sts.edit(f"<b>⭕ ʜᴇʀᴇ ɪs your original batch link containing `{og_msg}` files:\n{share_link}</b>", reply_markup=get_premium_buttons())

