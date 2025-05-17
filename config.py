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
API_ID = int(environ.get("API_ID", "25230605")) if environ.get("API_ID", "0").isdigit() else 0
API_HASH = environ.get("API_HASH", "b7d6c13e37d52cbbea25742f1c8b40cd")
BOT_TOKEN = environ.get("BOT_TOKEN", "")
BOT_USERNAME = environ.get("Mms_hub18_bot", "File_X_Sharing_Bot")  # without @
PORT = int(environ.get("PORT", "80"))

# Validate Bot API
if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("API_ID, API_HASH, and BOT_TOKEN are required!")

# Force subscription channel IDs
AUTH_CHANNEL = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('AUTH_CHANNEL', '-1002208751242').split()]

# Bot Start Pictures
PICS = environ.get('PICS', 
                   ' '
                   ' '
                   '').split()

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
DB_URI = environ.get("DB_URI", "mongodb+srv://facknet1999:GjMN6ZY5R3AbPx56@cluster0.6a3fnf0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = environ.get("DB_NAME", "Course-Empire")

# Auto Delete Information
AUTO_DELETE_MODE = is_enabled(environ.get('AUTO_DELETE_MODE', "True"))
AUTO_DELETE = int(environ.get("AUTO_DELETE", "20"))  # Time in minutes
AUTO_DELETE_TIME = int(environ.get("AUTO_DELETE_TIME", "1200"))  # Time in seconds

# Log Channel
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1002663679629"))

# File Caption
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)

# Public File Store
PUBLIC_FILE_STORE = is_enabled(environ.get('PUBLIC_FILE_STORE', "False"))

# Verify Mode Information
VERIFY_MODE = is_enabled(environ.get('VERIFY_MODE', "True"))
SHORTLINK_URL = environ.get("SHORTLINK_URL", "bharatlinks.com")
SHORTLINK_API = environ.get("SHORTLINK_API", "229853ecbbbbd01d73da405efce80c3acb8654ca")
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "https://t.me/alltutorial_mms/4")

# Ensure required variables for VERIFY_MODE
if VERIFY_MODE and not (SHORTLINK_URL and SHORTLINK_API):
    raise ValueError("VERIFY_MODE is enabled, but SHORTLINK_URL or SHORTLINK_API is missing.")

# Website Information
WEBSITE_URL_MODE = is_enabled(environ.get('WEBSITE_URL_MODE', "False"))
WEBSITE_URL = environ.get("WEBSITE_URL", "")

# File Stream Configuration
STREAM_MODE = is_enabled(environ.get('STREAM_MODE', "False"))
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
