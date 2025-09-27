import motor.motor_asyncio
from config import DB_NAME, DB_URI
from datetime import datetime

DATABASE_NAME = DB_NAME
DATABASE_URI = DB_URI

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups

    def new_user(self, id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            premium_status=dict(
                is_premium=False,
                expiry=None,
            ),
        )

    def new_group(self, id, title):
        return dict(
            id=id,
            title=title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    # Premium account management
    async def set_premium(self, user_id, expiry_datetime):
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {
                'premium_status.is_premium': True,
                'premium_status.expiry': expiry_datetime.isoformat()
            }},
            upsert=True
        )

    async def remove_premium(self, user_id):
        await self.col.update_one(
            {'id': int(user_id)},
            {'$set': {
                'premium_status.is_premium': False,
                'premium_status.expiry': None
            }},
            upsert=True
        )

    async def check_premium(self, user_id):
        user = await self.col.find_one({'id': int(user_id)})
        if user and user.get('premium_status', {}).get('is_premium'):
            expiry = user['premium_status'].get('expiry')
            if expiry is not None:
                try:
                    expiry_dt = datetime.fromisoformat(expiry)
                    return expiry_dt > datetime.now()
                except Exception:
                    pass
        return False

db = Database(DATABASE_URI, DATABASE_NAME)
