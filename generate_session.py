"""
Run this ONCE on your Mac to generate a SESSION_STRING.

  pip3 install telethon
  python3 generate_session.py

Then copy the printed string into the GitHub Secret named SESSION_STRING.
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input("API_ID: ").strip())
API_HASH = input("API_HASH: ").strip()

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n=== SESSION_STRING (copy ALL characters into the GitHub secret) ===\n")
    print(client.session.save())
    print("\n=== end ===")
