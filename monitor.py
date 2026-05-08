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
USD_PER_STAR = 0.013


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


def load_state():
    state = {"ids": [], "pending_msg_stars": 0}
    if SEEN_FILE.exists():
        try:
            loaded = json.loads(SEEN_FILE.read_text())
            if isinstance(loaded, list):
                state["ids"] = loaded  # migrate old list-only format
            elif isinstance(loaded, dict):
                state["ids"] = loaded.get("ids", [])
                state["pending_msg_stars"] = loaded.get("pending_msg_stars", 0)
        except Exception:
            pass
    return state


def save_state(state):
    if len(state["ids"]) > MAX_SEEN:
        state["ids"] = state["ids"][-MAX_SEEN:]
    SEEN_FILE.write_text(json.dumps(state))


def get_amount(stars_obj):
    if hasattr(stars_obj, "amount"):
        return stars_obj.amount
    return int(stars_obj)


async def main():
    state = load_state()
    seen_set = set(state["ids"])
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
        balance = get_amount(res.balance)

        if first_run:
            for tx in res.history:
                if tx.id not in seen_set:
                    state["ids"].append(tx.id)
                    seen_set.add(tx.id)
            print(f"First run: primed {len(state['ids'])} ids, balance {balance}")
        else:
            for tx in reversed(new_tx):  # oldest first
                state["ids"].append(tx.id)
                seen_set.add(tx.id)
                amount = get_amount(tx.amount)

                if amount == 1:
                    # 1-star message tip → buffer, don't notify yet
                    state["pending_msg_stars"] += 1
                    continue

                # Paid post → notify, including any buffered messages
                msg_id = getattr(tx, "msg_id", None)
                usd = amount * USD_PER_STAR
                lines = [f"⭐ +{amount} stars (=${usd:.2f}) received"]
                if msg_id:
                    lines.append(f"Post ID: {msg_id}")
                if state["pending_msg_stars"] > 0:
                    lines.append(f"+{state['pending_msg_stars']} stars for messages")
                    state["pending_msg_stars"] = 0
                lines.append(f"Balance: {balance} ⭐")
                notify("\n".join(lines))

            print(f"Found {len(new_tx)} new tx, balance {balance}, pending msgs {state['pending_msg_stars']}")

    save_state(state)


if __name__ == "__main__":
    asyncio.run(main())
