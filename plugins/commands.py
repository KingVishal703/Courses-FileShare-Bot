
import os
import logging
import random
import asyncio
from validators import domain
from Script import script
from plugins.dbusers import db
from pyrogram import Client, filters, enums
from plugins.users_api import get_user, update_user_info
from plugins.database import get_file_details
from pyrogram.errors import *
from pyrogram.types import *
from utils import verify_user, check_token, check_verification, get_token
from config import *
import re
import json
import base64
from urllib.parse import quote_plus
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size
logger = logging.getLogger(__name__)

BATCH_FILES = {}

async def is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
        except Exception as e:
            pass
    return btn

def get_size(size):
    """Get size in readable format"""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.premium import is_premium
from plugins.shortlink import make_shortlink
from plugins.database import get_file_details  # adjust according to your repo

# Tutorial aur Buy Premium ke URLs config me dalna
TUTORIAL_URL = "https://t.me/YourHelpChannel"
BUY_PREMIUM_URL = "https://t.me/YourSupportBot"
PREVIEW_IMAGE = "https://cdn-icons-png.flaticon.com/512/545/545674.png"


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    args = message.text.split(" ", 1)

    # Agar start ke saath file ID ya batch ID hai
    if len(args) > 1:
        encoded = args[1]
        try:
            decoded = base64.urlsafe_b64decode(encoded + "==").decode()
        except Exception:
            await message.reply_text("❌ Invalid link.")
            return

        # ---------------- Batch file handling ----------------
        if decoded.startswith("BATCH-"):
            batch_file_id = int(decoded.split("-")[1])
            try:
                msg = await client.get_messages(LOG_CHANNEL, batch_file_id)
                if not msg or not msg.document:
                    return await message.reply_text("❌ Batch file not found in storage.")
                local_file = await msg.download()
                with open(local_file, "r") as jf:
                    files = json.load(jf)
                for file_info in files:
                    file_type = None
                    if "file_id" in file_info:
                        try:
                            await client.send_cached_media(
                                chat_id=message.chat.id,
                                file_id=file_info["file_id"],
                                caption=file_info.get("caption", "")
                            )
                        except:
                            continue
                os.remove(local_file)
            except Exception:
                await message.reply_text("❌ Failed to fetch batch file.")
            return

        # ---------------- Single file handling ----------------
        if decoded.startswith("file_") or decoded.startswith("filep_"):
            try:
                file_msg_id = int(decoded.split("_")[1])
                msg = await client.get_messages(LOG_CHANNEL, file_msg_id)
                if not msg:
                    return await message.reply_text("❌ File not found in storage.")

                # Premium user -> direct file
                if await is_premium(user_id):
                    file_attr = msg.document or msg.video or msg.audio
                    await client.send_cached_media(
                        chat_id=message.chat.id,
                        file_id=file_attr.file_id,
                        caption=msg.caption or "Here is your file ✅"
                    )
                else:
                    # Free user -> shortlink + preview
                    original_url = f"https://t.me/{client.me.username}?start={encoded}"
                    short_url = await make_shortlink(original_url)
                    await message.reply_photo(
                        photo=PREVIEW_IMAGE,
                        caption="⚡ Get your file by completing the step below",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Open Link", url=short_url)],
                            [InlineKeyboardButton("📖 Tutorial", url=TUTORIAL_URL)],
                            [InlineKeyboardButton("💎 Buy Premium", url=BUY_PREMIUM_URL)]
                        ])
                    )
            except Exception:
                await message.reply_text("❌ File not found in storage.")
            return

    # ---------------- Normal /start ----------------
    await message.reply_text(
        "👋 Welcome to File Store Bot!\n\n"
        "📂 Send me any file and I will give you a sharable link.\n\n"
        "🆓 Free users: Get files via shortlink.\n"
        "💎 Premium users: Get direct downloads without ads."
                    )
                

@Client.on_message(filters.command('api') & filters.private)
async def shortener_api_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command

    if len(cmd) == 1:
        s = script.SHORTENER_API_MESSAGE.format(base_site=user["base_site"], shortener_api=user["shortener_api"])
        return await m.reply(s)

    elif len(cmd) == 2:    
        api = cmd[1].strip()
        await update_user_info(user_id, {"shortener_api": api})
        await m.reply("<b>Shortener API updated successfully to</b> " + api)


@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    text = f"`/base_site (base_site)`\n\n<b>Current base site: None\n\n EX:</b> `/base_site shortnerdomain.com`\n\nIf You Want To Remove Base Site Then Copy This And Send To Bot - `/base_site None`"
    if len(cmd) == 1:
        return await m.reply(text=text, disable_web_page_preview=True)
    elif len(cmd) == 2:
        base_site = cmd[1].strip()
        if base_site == None:
            await update_user_info(user_id, {"base_site": base_site})
            return await m.reply("<b>Base Site updated successfully</b>")
            
        if not domain(base_site):
            return await m.reply(text=text, disable_web_page_preview=True)
        await update_user_info(user_id, {"base_site": base_site})
        await m.reply("<b>Base Site updated successfully</b>")


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    
    elif query.data == "start":
        buttons = [
            # [
            # InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://youtube.com/@Tech_VJ')
            # ],
            [
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/+K57B1ypoxfM2NmE9')
            ],
            # [
            # InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')
            # ],
            [
            InlineKeyboardButton('💁‍♀️ Info', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    
    elif query.data == "clone":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CLONE_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )          

    
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )  


    elif query.data.startswith("generate_stream_link"):
        _, file_id = query.data.split(":")
        try:
            user_id = query.from_user.id
            username =  query.from_user.mention 

            log_msg = await client.send_cached_media(
                chat_id=LOG_CHANNEL,
                file_id=file_id,
            )
            fileName = {quote_plus(get_name(log_msg))}
            stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
            download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"

            xo = await query.message.reply_text(f'🔐')
            await asyncio.sleep(1)
            await xo.delete()


            button = [[
                InlineKeyboardButton("🚀 Fast Download 🚀", url=download),  # we download Link
                InlineKeyboardButton('🖥️ Stream online 🖥️', url=stream)
            ]]
            reply_markup=InlineKeyboardMarkup(button)
            await log_msg.reply_text(
                text=f"•ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ ꜰᴏʀ #{user_id} •• \n •ᴜꜱᴇʀɴᴀᴍᴇ : {username} \n •FileName : {fileName}",
                quote=True,
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            button = [[
                InlineKeyboardButton("🚀 Fast Download 🚀", url=download),  # we download Link
                InlineKeyboardButton('🖥️ Stream online 🖥️', url=stream)
            ],[
                InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
            ]]
            reply_markup=InlineKeyboardMarkup(button)
            await query.message.reply_text(
                text="•• ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ ☠︎⚔",
                quote=True,
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(e)  # print the error message
            await query.answer(f"☣something went wrong\n\n{e}", show_alert=True)
            return

