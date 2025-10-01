import motor.motor_asyncio
from datetime import datetime
from config import *

class Database:
    def __init__(self, uri, databasename):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client[databasename]
        self.col = self.db.users
        self.grp = self.db.groups

    def newuser(self, id, name):
        return dict(id=id, name=name, banstatus=dict(isbanned=False, banreason=""))

    def newgroup(self, id, title):
        return dict(id=id, title=title, chatstatus=dict(isdisabled=False, reason=""))

    async def adduser(self, id, name):
        user = self.newuser(id, name)
        await self.col.insert_one(user)

    async def isuserexist(self, id):
        user = await self.col.find_one({"id": int(id)})
        return bool(user)

    async def totaluserscount(self):
        count = await self.col.count_documents({})
        return count

    async def getallusers(self):
        cursor = self.col.find({})
        return cursor

    async def deleteuser(self, userid):
        await self.col.delete_many({"id": int(userid)})

    # Premium user functions added below

    async def add_premium_user(self, user_id: int, expiry_date: datetime):
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"premium": True, "premium_expiry": expiry_date}},
            upsert=True,
        )

    async def remove_premium_user(self, user_id: int):
        await self.col.update_one(
            {"id": user_id},
            {"$set": {"premium": False, "premium_expiry": None}},
        )

    async def check_premium(self, user_id: int):
        user = await self.col.find_one({"id": user_id})
        if user and user.get("premium") and user.get("premium_expiry"):
            if user["premium_expiry"] > datetime.utcnow():
                return True, user["premium_expiry"]
            else:
                # Premium expired, remove status
                await self.remove_premium_user(user_id)
                return False, None
        return False, None

db = Database(DBURI, DBNAME)
