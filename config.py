import os

ADMIN_IDS = os.getenv('ADMIN_IDS', '')
if ADMIN_IDS:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS.split(',')]
else:
    ADMIN_IDS = []  # 👈 Если пусто — пустой список

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
