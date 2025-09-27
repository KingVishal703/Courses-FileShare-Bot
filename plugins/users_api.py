import random
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME, SHORTENER_APIS

# MongoDB client
client = AsyncIOMotorClient(DB_URI)
db = client[DB_NAME]
col = db["users"]


# ---------------- User Functions ----------------
async def get_user(user_id: int):
    """Fetch user from DB or create if not exists."""
    user_id = int(user_id)
    user = await col.find_one({"user_id": user_id})
    if not user:
        user_data = {
            "user_id": user_id,
            "shortener_api": None,
            "base_site": None,
        }
        await col.insert_one(user_data)
        user = await col.find_one({"user_id": user_id})
    return user


async def update_user_info(user_id: int, value: dict):
    """Update user info."""
    user_id = int(user_id)
    await col.update_one({"user_id": user_id}, {"$set": value})


async def delete_user(user_id: int):
    """Delete user."""
    await col.delete_one({"user_id": int(user_id)})


async def total_users_count():
    """Return total number of users."""
    return await col.count_documents({})


async def get_all_users():
    """Return all users cursor."""
    return col.find({})


# ---------------- Short Link ----------------
async def get_short_link(user, url: str):
    """
    Generate short link using multiple providers.
    If none work, return original URL.
    """
    providers = SHORTENER_APIS.copy()
    random.shuffle(providers)  # Randomize provider order
    async with aiohttp.ClientSession() as session:
        for provider in providers:
            try:
                api_key = provider.get("api_key")
                base_site = provider.get("base_site")
                async with session.get(f"https://{base_site}/api?api={api_key}&url={url}", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "success":
                            return data.get("shortenedUrl")
            except Exception as e:
                # Ignore errors and try next provider
                continue
    # If all fail, return original URL
    return url
