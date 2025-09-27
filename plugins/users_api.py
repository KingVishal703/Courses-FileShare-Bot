import requests
import json
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME
from plugins.dbusers import db
from datetime import datetime

client = AsyncIOMotorClient(DB_URI)
database = client[DB_NAME]
col = database["users"]

import random
import aiohttp
from config import SHORTENER_APIS

async def get_short_link(user, url):
    providers = SHORTENER_APIS.copy()
    random.shuffle(providers)  # Randomize order, har baar alag try kare
    for api in providers:
        try:
            async with aiohttp.ClientSession() as session:
                api_key = api.get("api_key")
                base_site = api.get("base_site")
                resp = await session.get(f"https://{base_site}/api?api={api_key}&url={url}", timeout=10)
                resp_json = await resp.json()
                if resp.status == 200 and resp_json.get("status") == "success":
                    return resp_json.get("shortenedUrl")
        except Exception:
            continue
    # Sab fail ho jaaye to original link wapas
    return url
    

async def get_user(user_id):
    user_id = int(user_id)
    user = await col.find_one({"user_id": user_id})
    if not user:
        # New user initialization
        user = {
            "user_id": user_id,
            "shortener_api": None,
            "base_site": None,
            "premium_status": {
                "is_premium": False,
                "expiry": None
            }
        }
        await col.insert_one(user)
    return user

async def update_user_info(user_id, value: dict):
    user_id = int(user_id)
    myquery = {"user_id": user_id}
    newvalues = {"$set": value}
    await col.update_one(myquery, newvalues, upsert=True)

async def total_users_count():
    count = await col.count_documents({})
    return count

async def get_all_users():
    cursor = col.find({})
    return cursor

async def delete_user(user_id):
    await col.delete_one({'user_id': int(user_id)})


# Premium management wrappers using dbusers.py database methods

async def check_premium(user_id):
    return await db.check_premium(user_id)

async def set_premium(user_id, expiry_datetime):
    await db.set_premium(user_id, expiry_datetime)

async def remove_premium(user_id):
    await db.remove_premium(user_id)
    
