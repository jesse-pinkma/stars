import os
import json
import asyncio
import urllib.request
import urllib.parse
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import functions

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION_STRING"]
CHANNEL = os.environ["CHANNEL"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

SEEN_FILE = Path("seen.json")
MAX_SEEN = 500


def notify(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    try:
        resp = urllib.request.urlopen(url, data=data, timeout=10).read()
        print(f"notify ok: {resp[:200]}")
    except Exception as e:
        print(f"notify FAILED: {type(e).__name__}: {e}")
        if hasattr(e, "read"):
            print(f"body: {e.read()[:500]}")

async def main():
    notify("🟢 monitor ran")
    seen = []
    if SEEN_FILE.exists():
        try:
            seen = json.loads(SEEN_FILE.read_text())
        except Exception:
            seen = []
    seen_set = set(seen)
    first_run = len(seen_set) == 0

    async with TelegramClient(StringSession(SESSION), API_ID, API_HASH) as client:
        peer = await client.get_input_entity(CHANNEL)
        res = await client(functions.payments.GetStarsTransactionsRequest(
            peer=peer,
            offset="",
            limit=50,
            inbound=True,
            outbound=False,
        ))

        new_tx = [tx for tx in res.history if tx.id not in seen_set]

        if first_run:
            for tx in res.history:
                if tx.id not in seen_set:
                    seen.append(tx.id)
                    seen_set.add(tx.id)
            print(f"First run: primed {len(seen)} ids, balance {res.balance.amount}")
        else:
            for tx in reversed(new_tx):
                seen.append(tx.id)
                seen_set.add(tx.id)
                amount = tx.stars.amount
                msg_id = getattr(tx, "msg_id", None)
                title = (
                    getattr(tx, "title", None)
                    or getattr(tx, "description", "")
                    or "paid post"
                )
                text = (
                    f"⭐ +{amount} stars received\n"
                    f"Item: {title}"
                    + (f"\nPost ID: {msg_id}" if msg_id else "")
                    + f"\nBalance: {res.balance.amount} ⭐"
                )
                notify(text)
            print(f"Found {len(new_tx)} new tx, balance {res.balance.amount}")

    if len(seen) > MAX_SEEN:
        seen = seen[-MAX_SEEN:]
    SEEN_FILE.write_text(json.dumps(seen))


if __name__ == "__main__":
    asyncio.run(main())
