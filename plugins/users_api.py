import random
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME, SHORTENER_APIS
from plugins.dbusers import db as db_module

# ------------------- Database Connection -------------------
client = AsyncIOMotorClient(DB_URI)
db = client[DB_NAME]
col = db["users"]

# ------------------- User Management -------------------
async def get_user(user_id: int):
    user_id = int(user_id)
    user = await col.find_one({"user_id": user_id})
    if not user:
        user_data = {"user_id": user_id, "shortener_api": None, "base_site": None}
        await col.insert_one(user_data)
        user = await col.find_one({"user_id": user_id})
    return user

async def update_user_info(user_id: int, data: dict):
    user_id = int(user_id)
    await col.update_one({"user_id": user_id}, {"$set": data}, upsert=True)

async def delete_user(user_id: int):
    user_id = int(user_id)
    await col.delete_one({"user_id": user_id})

async def total_users_count():
    return await col.count_documents({})

async def get_all_users():
    return col.find({})

# ------------------- Premium Handling -------------------
async def check_premium(user_id: int) -> bool:
    user = await col.find_one({"user_id": int(user_id)})
    if not user:
        return False
    expiry = user.get("premium_expiry")
    if expiry and expiry > datetime.now():
        return True
    return False

async def set_premium(user_id: int, expiry_date):
    await update_user_info(user_id, {"premium_expiry": expiry_date})

async def remove_premium(user_id: int):
    await update_user_info(user_id, {"premium_expiry": None})

# ------------------- Shortener Logic -------------------
async def get_short_link(user: dict, url: str):
    """
    Returns a short link using user's custom API or random global SHORTENER_APIS
    """
    # Prefer user's own shortener API
    if user.get("shortener_api") and user.get("base_site"):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"https://{user['base_site']}/api?api={user['shortener_api']}&url={url}", timeout=10) as resp:
                    resp_json = await resp.json()
                    if resp.status == 200 and resp_json.get("status") == "success":
                        return resp_json.get("shortenedUrl")
            except Exception:
                pass  # fallback to global shorteners

    # Try global shorteners
    providers = SHORTENER_APIS.copy()
    random.shuffle(providers)
    async with aiohttp.ClientSession() as session:
        for api in providers:
            try:
                api_key = api.get("api_key")
                base_site = api.get("base_site")
                async with session.get(f"https://{base_site}/api?api={api_key}&url={url}", timeout=10) as resp:
                    resp_json = await resp.json()
                    if resp.status == 200 and resp_json.get("status") == "success":
                        return resp_json.get("shortenedUrl")
            except Exception:
                continue

    # If all fails, return original URL
    return url
