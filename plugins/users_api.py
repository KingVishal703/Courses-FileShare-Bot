import random
import aiohttp
from config import SHORTENER_APIS
from plugins.dbusers import db


# ---------- USER HANDLING ----------
async def get_user(user_id: int):
    """User fetch karo, agar nahi mila to insert karo"""
    user = await db.col.find_one({'user_id': int(user_id)})
    if not user:
        user_data = {
            "user_id": int(user_id),
            "shortener_api": None,
            "base_site": None
        }
        await db.col.insert_one(user_data)
        user = await db.col.find_one({'user_id': int(user_id)})
    return user


async def update_user_info(user_id: int, data: dict):
    """User info update karo"""
    await db.col.update_one({'user_id': int(user_id)}, {'$set': data}, upsert=True)


async def check_premium(user_id: int):
    """Premium check karo (dbusers.py ke function se)"""
    return await db.check_premium(user_id)


# ---------- SHORTLINK HANDLING ----------
async def get_short_link(user, url: str):
    """
    Agar user ke paas apna API hai use karo,
    warna random global SHORTENER_APIS list se try karo
    """
    # User ke custom API
    if user.get("shortener_api") and user.get("base_site"):
        api_key = user["shortener_api"]
        base_site = user["base_site"]
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"https://{base_site}/api?api={api_key}&url={url}",
                    timeout=10
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("status") == "success":
                        return data.get("shortenedUrl")
            except Exception:
                pass  # fallback to global providers

    # Global providers (config me SHORTENER_APIS)
    providers = SHORTENER_APIS.copy()
    random.shuffle(providers)
    async with aiohttp.ClientSession() as session:
        for api in providers:
            try:
                api_key = api.get("api_key")
                base_site = api.get("base_site")
                async with session.get(
                    f"https://{base_site}/api?api={api_key}&url={url}",
                    timeout=10
                ) as resp:
                    resp_json = await resp.json()
                    if resp.status == 200 and resp_json.get("status") == "success":
                        return resp_json.get("shortenedUrl")
            except Exception:
                continue

    # Agar sab fail ho jaye → original link return karo
    return url
