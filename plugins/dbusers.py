from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME
from datetime import datetime

client = AsyncIOMotorClient(DB_URI)
db = client[DB_NAME]
col = db["users"]
grp = db["groups"]

class Database:

    def __init__(self):
        self.col = col
        self.grp = grp

    # ---------- USER MANAGEMENT ----------
    def new_user(self, user_id: int, first_name: str):
        return dict(
            user_id=user_id,
            first_name=first_name,
            premium=False,
            premium_expiry=None,
            ban_status=dict(
                is_banned=False,
                ban_reason=""
            )
        )

    async def add_user(self, user_id: int, first_name: str):
        user = await self.col.find_one({"user_id": user_id})
        if not user:
            await self.col.insert_one(self.new_user(user_id, first_name))

    async def is_user_exist(self, user_id: int) -> bool:
        user = await self.col.find_one({"user_id": user_id})
        return user is not None

    async def total_users_count(self) -> int:
        return await self.col.count_documents({})

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id: int):
        await self.col.delete_many({"user_id": int(user_id)})

    # ---------- PREMIUM MANAGEMENT ----------
    async def set_premium(self, user_id: int, expiry_date: datetime):
        await self.col.update_one(
            {"user_id": user_id},
            {"$set": {"premium": True, "premium_expiry": expiry_date}},
            upsert=True
        )

    async def remove_premium(self, user_id: int):
        await self.col.update_one(
            {"user_id": user_id},
            {"$set": {"premium": False, "premium_expiry": None}}
        )

    async def check_premium(self, user_id: int) -> bool:
        user = await self.col.find_one({"user_id": user_id})
        if not user:
            return False
        if user.get("premium") and user.get("premium_expiry"):
            if user["premium_expiry"] > datetime.utcnow():
                return True
            else:
                # Agar expire ho gaya to reset kar do
                await self.remove_premium(user_id)
                return False
        return False


# Global object for import
db = Database()
