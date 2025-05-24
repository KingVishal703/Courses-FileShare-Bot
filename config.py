import re
import os
from os import environ
from Script import script  # Ensure 'Script' module is available

# ID validation pattern
id_pattern = re.compile(r'^-?\d+$')

# Helper function to check boolean values
def is_enabled(value, default=False):
    if isinstance(value, str):
        if value.lower() in ["true", "yes", "1", "enable", "y"]:
            return True
        elif value.lower() in ["false", "no", "0", "disable", "n"]:
            return False
    return default

# Bot Information
API_ID = int(environ.get("API_ID", "")) if environ.get("API_ID", "0").isdigit() else 0
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")
BOT_USERNAME = environ.get("BOT_USERNAME", "File_X_Sharing_Bot")  # without @
PORT = int(environ.get("PORT", "80"))

# Validate Bot API
if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("API_ID, API_HASH, and BOT_TOKEN are required!")

# Force subscription channel IDs
AUTH_CHANNEL = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('AUTH_CHANNEL', '-1002394633791').split()]

# Bot Start Pictures
PICS = environ.get('PICS', 
                   'https://graph.org/file/4841dcdcc8b6184847b33-db7006da59fb885b42.jpg '
                   'https://graph.org/file/6cee69f25da9ae5a833e6-e96e9b204569966133.jpg '
                   'https://graph.org/file/962a8ff5525ed8640afe8-5a63755db724b4bc37.jpg').split()

# Admin IDs
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '5654093580').split()]

# Clone Information
CLONE_MODE = is_enabled(environ.get('CLONE_MODE', "False"))
CLONE_DB_URI = environ.get("CLONE_DB_URI", "")
CDB_NAME = environ.get("CDB_NAME", "")

# Ensure required variables for CLONE_MODE
if CLONE_MODE and not (CLONE_DB_URI and CDB_NAME):
    raise ValueError("CLONE_MODE is enabled, but CLONE_DB_URI or CDB_NAME is missing.")

# Database Information
DB_URI = environ.get("DB_URI", "mongodb+srv://bevag22776:LTYSLtfLKt2KCMnD@cluster0.6z90l.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = environ.get("DB_NAME", "Course-Empire")

# Auto Delete Information
AUTO_DELETE_MODE = is_enabled(environ.get('AUTO_DELETE_MODE', "True"))
AUTO_DELETE = int(environ.get("AUTO_DELETE", "20"))  # Time in minutes
AUTO_DELETE_TIME = int(environ.get("AUTO_DELETE_TIME", "1200"))  # Time in seconds

# Log Channel
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1002309157883"))

# File Caption
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)

# Public File Store
PUBLIC_FILE_STORE = is_enabled(environ.get('PUBLIC_FILE_STORE', "False"))

# Verify Mode Information
VERIFY_MODE = is_enabled(environ.get('VERIFY_MODE', "False"))
SHORTLINK_URL = environ.get("SHORTLINK_URL", "jiolink.net")
SHORTLINK_API = environ.get("SHORTLINK_API", "be0c4404baa0485a6094e5f56a4e3a48bdabbcee")
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "https://t.me/hentai_Hanime_Update_Channel/30")

# Ensure required variables for VERIFY_MODE
if VERIFY_MODE and not (SHORTLINK_URL and SHORTLINK_API):
    raise ValueError("VERIFY_MODE is enabled, but SHORTLINK_URL or SHORTLINK_API is missing.")

# Website Information
WEBSITE_URL_MODE = is_enabled(environ.get('WEBSITE_URL_MODE', "True"))
WEBSITE_URL = environ.get("WEBSITE_URL", "https://worldurl.42web.io/")

# File Stream Configuration
STREAM_MODE = is_enabled(environ.get('STREAM_MODE', "True"))
MULTI_CLIENT = is_enabled(environ.get('MULTI_CLIENT', "True"))
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes

# Heroku Environment Detection
ON_HEROKU = 'DYNO' in environ
URL = environ.get("URL", "")

# Final Checks
if STREAM_MODE and not URL:
    raise ValueError("STREAM_MODE is enabled, but URL is missing.")

print("Configuration loaded successfully.")
