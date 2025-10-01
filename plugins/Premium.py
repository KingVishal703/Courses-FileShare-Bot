import os import asyncio from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient from pyrogram import Client, filters from pyrogram.types import Message

Try to read config from repo config.py; fallback to env variables

try: from config import MONGO_DB_URL, ADMINS except Exception: MONGO_DB_URL = os.environ.get("MONGO_DB_URL") # ADMINS expected as list of ints or single int; fallback to environment comma-separated adm = os.environ.get("ADMINS", "") if adm: ADMINS = [int(x.strip()) for x in adm.split(",") if x.strip()] else: ADMINS = []

if not MONGO_DB_URL: raise RuntimeError("MONGO_DB_URL is required in config.py or environment variables")

mongo = AsyncIOMotorClient(MONGO_DB_URL) db = mongo.get_default_database()  # uses DB from connection string premium_coll = db.get_collection("premium_users")

async def _now_utc(): return datetime.now(timezone.utc)

async def add_premium(user_id: int, days: int) -> datetime: """Add or extend premium for user_id by days. Returns expiry datetime (UTC).""" now = await _now_utc() doc = await premium_coll.find_one({"user_id": int(user_id)}) if doc and doc.get("expires_at"): current_expiry = doc["expires_at"] if isinstance(current_expiry, datetime): base = current_expiry if current_expiry > now else now else: base = now else: base = now

new_expiry = base + timedelta(days=int(days))
await premium_coll.update_one({"user_id": int(user_id)}, {"$set": {"expires_at": new_expiry}}, upsert=True)
return new_expiry

async def remove_premium(user_id: int) -> bool: """Remove premium record for user_id. Returns True if removed or existed.""" res = await premium_coll.delete_one({"user_id": int(user_id)}) return res.deleted_count > 0

async def get_premium_expiry(user_id: int): """Return expiry datetime in UTC or None""" doc = await premium_coll.find_one({"user_id": int(user_id)}) if not doc: return None return doc.get("expires_at")

async def is_premium(user_id: int) -> bool: """Check if user is premium (expiry in future).""" doc = await premium_coll.find_one({"user_id": int(user_id)}) if not doc: return False expires_at = doc.get("expires_at") if not expires_at: return False now = await _now_utc() return expires_at > now

-----------------------

Pyrogram command handlers

-----------------------

The plugin uses class decorator style used in the repo (Client.on_message)

@Client.on_message(filters.command("add_premium") & filters.user(ADMINS)) async def _cmd_add_premium(c: Client, m: Message): """Usage: /add_premium <user_id> <days> or reply to a user with: /add_premium <days> """ args = m.text.split() target_id = None days = None

# If admin replied to a user's message, use that user's id
if m.reply_to_message:
    target_id = m.reply_to_message.from_user.id
    if len(args) >= 2:
        try:
            days = int(args[1])
        except Exception:
            days = None
else:
    if len(args) >= 3:
        try:
            target_id = int(args[1])
            days = int(args[2])
        except Exception:
            await m.reply_text("Usage: /add_premium <user_id> <days>  (or reply with /add_premium <days>)")
            return

if not target_id or not days:
    await m.reply_text("Usage: /add_premium <user_id> <days>  (or reply with /add_premium <days>)")
    return

new_expiry = await add_premium(target_id, days)
await m.reply_text(f"✅ Added premium to `{target_id}` for {days} day(s). Expires at: {new_expiry.isoformat()}")

@Client.on_message(filters.command("remove_premium") & filters.user(ADMINS)) async def _cmd_remove_premium(c: Client, m: Message): """Usage: /remove_premium <user_id> or reply to a user""" args = m.text.split() target_id = None if m.reply_to_message: target_id = m.reply_to_message.from_user.id else: if len(args) >= 2: try: target_id = int(args[1]) except Exception: await m.reply_text("Usage: /remove_premium <user_id> (or reply to a user)") return

if not target_id:
    await m.reply_text("Usage: /remove_premium <user_id> (or reply to a user)")
    return

removed = await remove_premium(target_id)
if removed:
    await m.reply_text(f"✅ Premium removed for `{target_id}`")
else:
    await m.reply_text(f"ℹ️ No premium record found for `{target_id}`")

@Client.on_message(filters.command("check_premium") & filters.user(ADMINS)) async def _cmd_check_premium(c: Client, m: Message): """Usage: /check_premium <user_id> or reply to a user""" args = m.text.split() target_id = None if m.reply_to_message: target_id = m.reply_to_message.from_user.id else: if len(args) >= 2: try: target_id = int(args[1]) except Exception: await m.reply_text("Usage: /check_premium <user_id> (or reply to a user)") return

if not target_id:
    await m.reply_text("Usage: /check_premium <user_id> (or reply to a user)")
    return

expiry = await get_premium_expiry(target_id)
if expiry and expiry > datetime.now(timezone.utc):
    await m.reply_text(f"✅ User `{target_id}` is premium. Expires at: {expiry.isoformat()}")
else:
    await m.reply_text(f"❌ User `{target_id}` is not premium or subscription expired.")

Optional: background task to clean expired docs (not necessary but useful)

async def _cleanup_expired_task(interval_hours: int = 24): while True: try: now = datetime.now(timezone.utc) await premium_coll.delete_many({"expires_at": {"$lte": now}}) except Exception: pass await asyncio.sleep(interval_hours * 3600)

If you want this task to run, import and schedule it from your main app startup code:

import asyncio

from plugins.premium import _cleanup_expired_task

asyncio.create_task(_cleanup_expired_task())

-----------------------

End of plugin

-----------------------

