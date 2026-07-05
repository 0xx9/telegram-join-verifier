# telegram-join-verifier

Bot for private Telegram channels that require join request approval. When someone requests to join, the bot DMs them a verification button. Only after they click it does the request get approved.

Simple anti-spam layer before people land in your channel.

## How it works

1. User sends a join request to your private channel
2. Bot messages them with an "I'm not a bot" button
3. They click it → join request approved

If the user never started the bot before, the DM won't go through — they'll need to find the bot and hit `/start` first, then re-request to join.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# put your BOT_TOKEN in .env
python bot.py
```

### Channel config

- Add the bot as admin on your channel
- Give it **"Add Members"** permission (needed to approve requests)
- Enable **"Approve New Members"** in channel settings

## Env

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | From @BotFather |
| `ADMIN_ID` | Your Telegram user ID (optional, for admin commands) |

Pending requests are kept in memory — a restart clears them. Users can just send the join request again.

## send_pending.py

Separate script for batch-sending messages to users stored in `users.json`. Useful if you collected user IDs and want to reach them later.
