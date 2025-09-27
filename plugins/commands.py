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
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils import verify_user, check_token, check_verification, get_token
from config import *
import re
import json
import base64
from urllib.parse import quote_plus
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size
from datetime import datetime, timedelta
from config import ADMINS

logger = logging.getLogger(__name__)
BATCH_FILES = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def get_premium_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL)],
        [InlineKeyboardButton("Buy Premium", callback_data="buy_premium")]
    ])


# ✅ Add Premium
@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def handle_addpremium(client, message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.reply_text("Usage: /addpremium <user_id> <7day|1month|3month>")
            return

        user_id = int(parts[1])
        duration_map = {'7day': 7, '1month': 30, '3month': 90}
        days = duration_map.get(parts[2].lower())

        if not days:
            await message.reply_text("❌ Duration galat hai. Options: 7day, 1month, 3month.")
            return

        expiry_dt = datetime.now() + timedelta(days=days)
        await db.set_premium(user_id, expiry_dt)

        await message.reply_text(f"✅ User `{user_id}` ko {parts[2]} ke liye premium diya gaya hai.")

    except Exception as e:
        await message.reply_text(f"Error: {e}")


# ✅ Remove Premium
@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def handle_removepremium(client, message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply_text("Usage: /removepremium <user_id>")
            return

        user_id = int(parts[1])
        await db.remove_premium(user_id)
        await message.reply_text(f"✅ User `{user_id}` ka premium hata diya gaya hai.")

    except Exception as e:
        await message.reply_text(f"Error: {e}")


# ✅ Check Subscription
async def is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
        except Exception:
            pass
    return btn


# ✅ Start Command
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if AUTH_CHANNEL:
        try:
            btn = await is_subscribed(client, message, AUTH_CHANNEL)
            if btn:
                username = (await client.get_me()).username
                if len(message.command) > 1:
                    btn.append([InlineKeyboardButton("♻️ Try Again ♻️",
                                                     url=f"https://t.me/{username}?start={message.command[1]}")])
                else:
                    btn.append([InlineKeyboardButton("♻️ Try Again ♻️",
                                                     url=f"https://t.me/{username}?start=true")])
                await message.reply_text(
                    text=f"<b>👋 Hello {message.from_user.mention},\nकृपया नीचे दिए गए चैनल को join करें और Try again बटन पर क्लिक करें। 🙂</b>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
        except Exception as e:
            print(e)

    username = (await client.get_me()).username
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL,
                                  script.LOG_TEXT.format(message.from_user.id, message.from_user.mention))

    if len(message.command) != 2:
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
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('🤖 Create Your Own Clone Bot', callback_data='clone')])

        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, me2),
            reply_markup=reply_markup
        )


# ✅ Callback Handler
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "close_data":
        await query.message.delete()

    elif data == "buy_premium":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("₹10 - 7 days", callback_data="buy_7day")],
            [InlineKeyboardButton("₹30 - 1 month", callback_data="buy_1month")],
            [InlineKeyboardButton("₹60 - 3 months", callback_data="buy_3month")],
            [InlineKeyboardButton("Close", callback_data="close_buy")]
        ])
        await query.message.edit_text("Choose your premium plan:", reply_markup=buttons)

    elif data.startswith("buy_"):
        plan = data.split("_")[1]
        payment_info = {
            "7day": "UPI ID ya QR code for 7 days plan",
            "1month": "UPI ID ya QR code for 1 month plan",
            "3month": "UPI ID ya QR code for 3 months plan"
        }
        await query.message.edit_text(
            f"Please send payment for the **{plan}** plan:\n\n{payment_info[plan]}\n\n"
            f"After payment, send your screenshot to admin: [Admin Telegram](https://t.me/ADMIN_USERNAME)",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close_buy")]])
        )

    elif data == "close_buy":
        await query.message.delete()
