# Telegram Channel Stars Monitor (GitHub Actions)

Sends you a Saved-Messages notification every time someone buys a paid post on your channel. Polls every 5 minutes (GitHub Actions cron minimum). Free, no server.

## One-time setup

### 1. Get Telegram API credentials
Go to <https://my.telegram.org> → **API development tools** → create an app.
Copy the `api_id` (number) and `api_hash` (string).

### 2. Generate a SESSION_STRING locally (one time only)
On your Mac:
```bash
pip3 install telethon
python3 generate_session.py
```
Enter your `api_id` / `api_hash`, then your phone number, then the Telegram code.
Copy the long printed string — that's your `SESSION_STRING`.

### 3. Create a PRIVATE GitHub repo
Upload all files in this folder. **Must be private** — the seen.json will track your transaction IDs.

### 4. Add repository secrets
Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
Add five secrets:

| Name             | Value                                           |
|------------------|-------------------------------------------------|
| `API_ID`         | from step 1                                     |
| `API_HASH`       | from step 1                                     |
| `SESSION_STRING` | from step 2                                     |
| `CHANNEL`        | your channel username e.g. `@yourchannel`       |
| `NOTIFY_TO`      | `me` (Saved Messages) or your `@username`       |

### 5. Trigger the first run
Repo → **Actions** tab → **stars-monitor** → **Run workflow**.
First run primes `seen.json` with existing transactions (no notifications).
Subsequent runs notify you of new sales only.

## What you'll get
A message in your Telegram Saved Messages every time someone buys a paid post:
```
⭐ +100 stars received
Item: paid post
Post ID: 1234
Balance: 4500 ⭐
```

## Notes
- Polls every 5 min — that's GitHub's hard minimum for cron schedules.
- GitHub may delay scheduled runs during peak load; expect occasional drift.
- Free tier gives 2,000 Actions minutes/month; this uses ~30 sec/run × 12/hour × 24 × 30 ≈ 720 min/month. Well under the limit.
- If the workflow fails repeatedly with auth errors, regenerate the SESSION_STRING (Telegram occasionally invalidates them).
- Disable: Repo → Actions → stars-monitor → "..." → Disable workflow.
