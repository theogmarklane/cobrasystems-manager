# 🐍 Cobra Systems™ Manager

A powerful, modern Discord server management bot written in Python using **discord.py**.

## Features

### 🛡️ Moderation
- `ban` / `unban` — Ban and unban users
- `kick` — Kick members
- `mute` / `timeout` / `unmute` — Timeout members (supports `10m`, `1h`, `2d` etc.)
- `warn` / `warnings` / `clearwarns` — Warning system with persistent storage
- `purge` / `clear` — Bulk delete messages (optionally filter by user)
- `lock` / `unlock` — Lock and unlock channels
- `slowmode` — Set channel slowmode

### 🎭 Roles & Automation
- **Auto Role** — Automatically give a role when someone joins
- **Welcome Messages** — Customizable welcome embeds
- **Reaction Roles** — Create reaction role menus easily
- **Tickets** — Button-based ticket panel for support, purchase, bugs, and other requests, with transcripts and close logs
- `giverole` / `takerole` — Manually manage roles
- Moderation logging channel

### 🔧 Utility
- `help` — Beautiful command overview
- `ping` / `uptime`
- `userinfo` / `serverinfo` / `avatar` / `roleinfo`

### 💰 Economy
- `balance` — Check your balance or another member's balance
- `daily` / `work` — Earn coins on cooldowns
- `give` — Transfer coins to another member
- `leaderboard` — Show the richest members in the server
- `addmoney` / `removemoney` / `setmoney` / `resetmoney` — Manage balances as the bot owner, server owner, or a server administrator

All commands work as both **slash commands** (`/ban`) and **prefix commands** (`!ban`).

---

## Setup Guide

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → name it `Cobra Systems™ Manager`
3. Go to the **Bot** tab → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - ✅ Presence Intent (optional)
   - ✅ Server Members Intent (**required**)
   - ✅ Message Content Intent (**required**)
5. Copy the **Bot Token**

### 2. Invite the Bot

Use this URL (replace `CLIENT_ID` with your Application ID):

```
https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

Or generate one in the Developer Portal → OAuth2 → URL Generator  
(Select `bot` + `applications.commands` scopes and Administrator permission for easiest setup).

### 3. Install & Run

#### Option A: Docker (easiest)

```bash
# Create your env file first
cp .env.example .env

# Build and run in one command
docker compose up -d --build
```

To view logs:
```bash
docker compose logs -f
```

To stop:
```bash
docker compose down
```

#### Option B: Local Python

```bash
# Clone / download the bot folder
cd cobra_systems_manager

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
# Then edit .env and put your token + your Discord user ID
```

Your `.env` should look like:
```env
DISCORD_TOKEN=MTIz...your_token_here
OWNER_ID=123456789012345678
# Optional: instant slash-command registration in one development server
DISCORD_GUILD_ID=123456789012345678
```

The Docker image loads every cog before registering commands. Set
`DISCORD_GUILD_ID` in `.env` to preload all slash commands immediately in a
server; without it, commands are registered globally and Discord can take up
to an hour to display updates.

Then start the bot:
```bash
python bot.py
```

---

## Docker Files Included

- `Dockerfile` — Container image for the bot
- `docker-compose.yml` — One-command run setup
- `.dockerignore` — Smaller/faster Docker builds
- `.env.example` — Environment variable template

---

## Recommended First Setup (in your server)

```
/setlog #mod-logs          → Enable moderation logs
/welcome #welcome          → Enable welcome messages
/autorole @Member          → Auto-role on join
/reactionrole "Roles" "React to get roles!" 🎮 @Gamer
/ticketpanel #tickets      → Post a ticket panel
/ticketpanel #tickets #ticket-logs → Also send transcripts and close logs there
```

---

## File Structure

```
cobra_systems_manager/
├── bot.py              # Main entry point
├── config.json         # Persistent config (auto roles, channels, reaction roles)
├── requirements.txt
├── .env                # Your secrets (never share this)
├── data/
│   └── warnings.json   # Warning storage
└── cogs/
    ├── events.py       # Join/leave, logging
    ├── moderation.py   # All mod commands
    ├── tickets.py      # Ticket panel and ticket channels
    ├── roles.py        # Auto role, reaction roles, welcome
    └── utility.py      # Help, info commands
```

---

## Notes

- The bot uses **hybrid commands** — both `/slash` and `!prefix` work.
- Reaction roles and config are saved in `config.json`.
- Warnings are saved in `data/warnings.json`.
- Make sure the bot's role is **above** any roles it needs to manage.
- For production, consider using a process manager like `pm2` or `systemd`.

---

**Cobra Systems™ Manager** — Keep your server under control. 🐍
