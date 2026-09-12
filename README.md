# Stone FFA Discord Bot

Production-ready Discord bot for the **Stone FFA** Minecraft Free-For-All community.

Built with **Python 3.12+** (compatible with Python 3.14 when available), `discord.py` 2.x, SQLAlchemy async, and a modular cog architecture.

## Features

- **Information commands** – `/server`, `/ip`, `/store`, `/vote`, `/website`, `/discord`, `/help`
- **Minecraft status** – `/status` via public API (`api.mcsrvstat.us`)
- **Player lookup placeholder** – `/player` ready for future Mojang/server integration
- **Moderation** – `/warn`, `/warnings`, `/kick`, `/ban`, `/unban`, `/timeout`, `/untimeout`, `/mute`, `/unmute`, `/purge`, `/slowmode`
- **Staff logging** – joins, leaves, message edits/deletes, moderation actions, tickets
- **Ticket system** – panel button, private channels, close confirmation, basic transcript logging
- **Welcome + auto-role** – configurable channel and role on join
- **Verification panel** – button that records intent (Minecraft account linking can be added later)
- **SQLite database** by default (PostgreSQL-ready via `DATABASE_URL`)
- **Slash commands**, embeds, persistent buttons, proper permission checks

## Requirements

- **Python 3.12 or newer** (project targets modern Python; 3.14 when your environment provides it)
- A Discord application/bot token
- Network access for Discord API and optional Minecraft status API

## Installation

```bash
git clone https://github.com/ksskdiusmdjdikdk-blip/stone-ffa-discord-bot.git
cd stone-ffa-discord-bot

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Creating a Discord Bot Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → name it (e.g. Stone FFA Bot)
3. **Bot** tab → **Reset Token** → copy the token (you will put this in `.env`)
4. Enable **Privileged Gateway Intents**:
   - Server Members Intent
   - Message Content Intent
5. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot permissions (recommended):
     - Manage Channels
     - Kick Members
     - Ban Members
     - Moderate Members
     - Manage Messages
     - Send Messages
     - Embed Links
     - Attach Files
     - Read Message History
     - View Channels
6. Invite the bot to your server with the generated URL

## Configuration (`.env`)

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | **Required** bot token |
| `GUILD_ID` | Your Discord server ID (recommended in development for instant slash sync) |
| `DATABASE_URL` | Default SQLite path is fine |
| `LOG_CHANNEL_ID` | Channel for join/leave/edit/delete/ticket logs |
| `MOD_LOG_CHANNEL_ID` | Optional dedicated mod-action log |
| `WELCOME_CHANNEL_ID` | Welcome messages |
| `WELCOME_ROLE_ID` / `AUTO_ROLE_ID` | Roles assigned on join / verify |
| `STAFF_ROLE_ID` | Staff role for moderation + tickets |
| `TICKET_CATEGORY_ID` | Category for new ticket channels |
| `TICKET_SUPPORT_ROLE_ID` | Optional support role (falls back to staff) |
| `MINECRAFT_SERVER_IP` | Public server address (placeholder by default) |
| `MINECRAFT_SERVER_PORT` | Default `25565` |
| `STORE_URL`, `WEBSITE_URL`, `VOTE_URL`, `DISCORD_INVITE` | Public links |

**Never commit `.env`.** It is listed in `.gitignore`.

### Finding Discord IDs

Enable Developer Mode in Discord (Settings → Advanced), then right-click a server/channel/role → **Copy ID**.

## Running the Bot

```bash
source .venv/bin/activate
python -m bot.main
```

Or:

```bash
python bot/main.py
```

### Slash command sync

- If `GUILD_ID` is set, commands sync **only to that guild** (instant, best for development).
- If `GUILD_ID` is empty, commands sync **globally** (can take up to ~1 hour to appear everywhere).

For production: remove or blank `GUILD_ID` and restart once.

## Staff setup after invite

1. Create a staff role and set `STAFF_ROLE_ID`
2. Create log / welcome / ticket category channels and set their IDs
3. Run `/ticketpanel` in a support channel (staff only)
4. Run `/verifypanel` where you want verification (staff only)

## Commands overview

### Public

| Command | Description |
|---------|-------------|
| `/server` | Stone FFA info |
| `/ip` | Server IP |
| `/store` `/vote` `/website` `/discord` | Links |
| `/status` | Live Minecraft status |
| `/player <username>` | Player lookup (placeholder) |
| `/help` | Command list |

### Staff

| Command | Description |
|---------|-------------|
| `/warn` `/warnings` | Warnings |
| `/kick` `/ban` `/unban` | Kick / ban |
| `/timeout` `/untimeout` `/mute` `/unmute` | Timeouts |
| `/purge` `/slowmode` | Channel tools |
| `/ticketpanel` | Post ticket button |
| `/verifypanel` | Post verify button |

## Database

Default: SQLite file at `./data/stone_ffa.db`.

Tables: warnings, tickets, moderation_logs, verifications.

To use PostgreSQL later:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/stoneffa
```

Install `asyncpg` and adjust dependencies; the SQLAlchemy models do not need rewriting.

## Minecraft integration

- **Status**: [api.mcsrvstat.us](https://api.mcsrvstat.us/) (no API key). If the API is unreachable or the server is offline, `/status` reports offline gracefully.
- **Player lookup**: stub in `bot/services/minecraft.py`. Extend `MinecraftService.get_player` for Mojang API, a plugin bridge, or your own backend without changing command files.

## Deployment

- Use a process manager (`systemd`, `pm2`, Docker, etc.)
- Keep `.env` outside version control
- Prefer global command sync only after testing with `GUILD_ID`
- Ensure the host has outbound HTTPS to Discord and (optionally) mcsrvstat.us

## Troubleshooting

| Problem | What to check |
|---------|----------------|
| Bot does not start | `DISCORD_TOKEN` valid? Python ≥ 3.12? |
| Commands missing | Set `GUILD_ID` for instant sync, or wait for global sync |
| Cannot create tickets | Bot needs **Manage Channels**; category ID correct? |
| Auto-role fails | Bot role above target role; **Manage Roles** permission |
| Status always offline | Server actually offline, wrong IP, or status API blocked |
| Permission denied on staff commands | Assign `STAFF_ROLE_ID` or Administrator |

## Development

```bash
pip install -r requirements.txt
pytest
python -m compileall bot
```

## License

MIT – use and modify freely for your Stone FFA server.
