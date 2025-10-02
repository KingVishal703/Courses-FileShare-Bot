import logging
from struct import pack
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI, DB_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

COLLECTION_NAME = "Telegram_Files"

# MongoDB connection with error handling
try:
    client = AsyncIOMotorClient(DB_URI)
    db = client[DB_NAME]
    client.admin.command('ping')
    logger.info("MongoDB connected successfully.")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")

instance = Instance.from_db(db)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id', unique=True)
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    # ✅ New fields for safe restore
    chat_id = fields.IntField(required=True)
    msg_id = fields.IntField(required=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


# ✅ Save file details
async def save_file(file_id, file_ref, file_name, file_size, file_type,
                    mime_type, caption, chat_id, msg_id):
    try:
        media = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            caption=caption,
            chat_id=chat_id,
            msg_id=msg_id
        )
        await media.commit()
        return media
    except DuplicateKeyError:
        logger.warning(f"File already exists in DB: {file_id}")
    except Exception as e:
        logger.error(f"Error saving file to DB: {e}")


# ✅ Fetch file details
async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails[0] if filedetails else None


# 🔹 Legacy encoding (keep for compatibility)
def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    if not file_ref:
        return ""
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref or (None, None) on error"""
    try:
        decoded = FileId.decode(new_file_id)
        file_id = encode_file_id(
            pack(
                "<iiqq",
                int(decoded.file_type),
                decoded.dc_id,
                decoded.media_id,
                decoded.access_hash
            )
        )
        file_ref = encode_file_ref(decoded.file_reference)
        return file_id, file_ref
    except Exception as e:
        logger.error(f"Failed to decode file_id '{new_file_id}': {e}")
        return None, None
