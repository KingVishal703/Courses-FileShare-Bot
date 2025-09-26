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
from datetime import datetime, timedelta
from config import ADMINS  # Aapka admin list config se
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

BATCH_FILES = {}

# Premium users dictionary
premium_users = {}  # user_id: expiry_datetime

def is_admin(user_id):
    return user_id in ADMINS

def add_premium(user_id: int, days: int):
    expiry_date = datetime.now() + timedelta(days=days)
    premium_users[user_id] = expiry_date

def remove_premium(user_id: int):
    if user_id in premium_users:
        del premium_users[user_id]

def check_premium(user_id: int) -> bool:
    expiry = premium_users.get(user_id)
    if expiry and expiry > datetime.now():
        return True
    return False


@bot.message_handler(commands=['addpremium'])
def handle_addpremium(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Sirf admin hi is command ka use kar sakte hain.")
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        duration_map = {'7day': 7, '1month': 30, '3month': 90}
        duration = duration_map.get(parts[2].lower())
        if not duration:
            bot.reply_to(message, "Duration galat hai. 7day, 1month ya 3month use karein.")
            return
        add_premium(user_id, duration)
        bot.reply_to(message, f"User {user_id} ko {parts[2]} ke liye premium mila.")
    except Exception:
        bot.reply_to(message, "Usage: /addpremium <user_id> <7day|1month|3month>")


@bot.message_handler(commands=['removepremium'])
def handle_removepremium(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "Sirf admin hi is command ka use kar sakte hain.")
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        remove_premium(user_id)
        bot.reply_to(message, f"User {user_id} ka premium hata diya gaya hai.")
    except Exception:
        bot.reply_to(message, "Usage: /removepremium <user_id>")
        


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
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def get_premium_buttons():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("How To Open", url=VERIFY_TUTORIAL),
        InlineKeyboardButton("Buy Premium", callback_data="buy_premium")
    )
    return keyboard


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if AUTH_CHANNEL:
        try:
            btn = await is_subscribed(client, message, AUTH_CHANNEL)
            if btn:
                username = (await client.get_me()).username
                if len(message.command) > 1:
                    btn.append([InlineKeyboardButton("♻️ Try Again ♻️", url=f"<https://t.me/{username}?start={message.command>[1]}")])
                else:
                    btn.append([InlineKeyboardButton("♻️ Try Again ♻️", url=f"https://t.me/{username}?start=true")])
                await message.reply_text(text=f"<b>👋 Hello {message.from_user.mention}, कृपया नीचे दिए गए चैनल को join करें और Try again बटन पर क्लिक करें। 🙂\n\n Please join the channel then click on try again button. 😇</b>", reply_markup=InlineKeyboardMarkup(btn))
                return
        except Exception as e:
            print(e)
    username = (await client.get_me()).username
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(message.from_user.id, message.from_user.mention))
    if len(message.command) != 2:
        buttons = [
            [
            InlineKeyboardButton('🔍 Support Group', url='https://t.me/'),
            InlineKeyboardButton('🤖 Update Channel', url='https://t.me/+K57B1ypoxfM2NmE9')
            ],[
            InlineKeyboardButton('💁‍♀️ Info', callback_data='help'),
            InlineKeyboardButton('😊 About', callback_data='about')
        ]]
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('🤖 Create Your Own Clone Bot', callback_data='clone')])
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, me2),
            reply_markup=reply_markup
        )
        return

    # The rest of your existing message processing code here...
    # Attach get_premium_buttons() when sending any file/link share messages
    # For example: await message.reply("Your link here", reply_markup=get_premium_buttons())


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "close_data":
        await query.message.delete()

    elif data == "buy_premium":
        buttons = InlineKeyboardMarkup(row_width=1)
        buttons.add(
            InlineKeyboardButton("₹10 - 7 days", callback_data="buy_7day"),
            InlineKeyboardButton("₹30 - 1 month", callback_data="buy_1month"),
            InlineKeyboardButton("₹60 - 3 months", callback_data="buy_3month"),
            InlineKeyboardButton("Close", callback_data="close_buy")
        )
        await query.message.edit_text(
            "Choose your premium plan:",
            reply_markup=buttons
        )
    elif data.startswith("buy_"):
        plan = data.split("_")[1]
        payment_info = {
            "7day": "UPI ID ya QR code for 7 days plan",
            "1month": "UPI ID ya QR code for 1 month plan",
            "3month": "UPI ID ya QR code for 3 months plan"
        }
        await query.message.edit_text(
            f"Please send payment for the {plan} plan to this UPI:\n\n{payment_info[plan]}\n\nAfter payment, send your screenshot directly to admin: [Admin Telegram](https://t.me/ADMIN_USERNAME)",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close_buy")]])
        )
    elif data == "close_buy":
        await query.message.delete()

    # Add your additional callback query handlers below here as needed

