import os
import json
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import functions

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION_STRING"]
CHANNEL = os.environ["CHANNEL"]
NOTIFY_TO = os.environ.get("NOTIFY_TO", "me")

SEEN_FILE = Path("seen.json")
MAX_SEEN = 500


async def main():
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
            for tx in reversed(new_tx):  # oldest first
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
                await client.send_message(NOTIFY_TO, text)
            print(
                f"Found {len(new_tx)} new tx, balance {res.balance.amount}"
            )

    if len(seen) > MAX_SEEN:
        seen = seen[-MAX_SEEN:]
    SEEN_FILE.write_text(json.dumps(seen))


if __name__ == "__main__":
    asyncio.run(main())
