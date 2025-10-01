import motor.motor_asyncio
from config import DB_NAME, DB_URI

DATABASE_NAME = DB_NAME
DATABASE_URI = DB_URI

class Database:
    def __init__(self, uri, database_name):
        # Async MongoDB client
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups

        # Ensure unique index on user id (prevents duplicates)
        self.col.create_index("id", unique=True)

        # Test connection
        try:
            self._client.admin.command("ping")
            print("✅ MongoDB connected successfully.")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")

    # Template for a new user
    def new_user(self, id, name):
        return dict(
            id=int(id),
            name=name,
            ban_status=dict(is_banned=False, ban_reason=""),
        )

    # Template for a new group
    def new_group(self, id, title):
        return dict(
            id=int(id),
            title=title,
            chat_status=dict(is_disabled=False, reason=""),
        )

    # Add user (upsert: no duplicates)
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.update_one({'id': int(id)}, {'$setOnInsert': user}, upsert=True)

    # Check if user exists
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    # Total users count
    async def total_users_count(self):
        return await self.col.count_documents({})

    # Get all users as list
    async def get_all_users(self):
        cursor = self.col.find({})
        return [user async for user in cursor]

    # Delete user
    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})


# Instantiate database
db = Database(DATABASE_URI, DATABASE_NAME)
