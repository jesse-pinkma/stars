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


def load_state():
    state = {"ids": [], "pending_msg_stars": 0}
    if SEEN_FILE.exists():
        try:
            loaded = json.loads(SEEN_FILE.read_text())
            if isinstance(loaded, list):
                state["ids"] = loaded
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


def get_total_stars(stars_obj):
    if stars_obj is None:
        return 0
    if isinstance(stars_obj, (int, float)):
        return stars_obj
    whole = getattr(stars_obj, "amount", 0) or 0
    nanos = getattr(stars_obj, "nanos", 0) or 0
    return whole + nanos / 1e9


def fmt(s):
    return str(int(s)) if s == int(s) else f"{s:.2f}"


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
        balance = get_total_stars(res.balance)

        if first_run:
            for tx in res.history:
                if tx.id not in seen_set:
                    state["ids"].append(tx.id)
                    seen_set.add(tx.id)
            print(f"First run: primed {len(state['ids'])} ids, balance {balance}")
        else:
            for tx in reversed(new_tx):
                state["ids"].append(tx.id)
                seen_set.add(tx.id)

                stars = get_total_stars(getattr(tx, "amount", None))
                paid_msgs = getattr(tx, "paid_messages", None)

                # Paid message → buffer, no notification
                if paid_msgs:
                    if stars > 0:
                        state["pending_msg_stars"] += stars
                    continue

                # Skip 0-star or weird transactions
                if stars <= 0:
                    continue

                # Paid post → notify
                usd = stars * USD_PER_STAR
                lines = [f"⭐ +{fmt(stars)} stars (=${usd:.2f}) received"]
                if state["pending_msg_stars"] > 0:
                    lines.append(f"⭐ +{fmt(state['pending_msg_stars'])} stars for messages")
                    state["pending_msg_stars"] = 0
                lines.append(f"⭐ Balance: {fmt(balance)}")
                notify("\n".join(lines))

            print(f"Found {len(new_tx)} new tx, balance {balance}, pending {state['pending_msg_stars']}")

    save_state(state)


if __name__ == "__main__":
    asyncio.run(main())
