import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN_API')
GDRIVE_FOLDER_ID = os.getenv('GDRIVE_FOLDER_ID')
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv('GDRIVE_SERVICE_ACCOUNT_JSON')

# Telegram channel link for membership check
TELEGRAM_CHANNEL_LINK = os.getenv('TELEGRAM_CHANNEL_LINK')

# List of admin Telegram IDs
ADMINS = [6972153969, 987654321]  # Replace with real admin IDs

ALLOWED_DOMAINS = [
    'youtube.com', 'youtu.be', 't.me', 'telegram.me', 'example.com'
]

# YouTube links for guides and channel
YOUTUBE_SCREENSHOT_GUIDE_LINK = 'https://youtube.com/shorts/efmVhVG2fSQ?si=Mib9kEZacpw-z9-B'
YOUTUBE_LINK_GUIDE_LINK = 'https://youtube.com/shorts/pbtNmCYezOc?si=gwRKa0uAxkLCu258'
YOUTUBE_CHANNEL_LINK = 'https://youtube.com/@panda_groups?si=1Zzwjfa6de2B96g5'

# For backward compatibility (if needed elsewhere)
YOUTUBE_GUIDE_LINK = YOUTUBE_SCREENSHOT_GUIDE_LINK
