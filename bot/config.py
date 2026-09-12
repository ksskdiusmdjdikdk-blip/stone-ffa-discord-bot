"""Configuration loader for Stone FFA Discord bot.

All sensitive and environment-specific values come from environment variables
(or a .env file). Source code never contains secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _get_int(name: str, default: Optional[int] = None) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_color(name: str, default: int = 0x2F3136) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        if raw.lower().startswith("0x"):
            return int(raw, 16)
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    discord_token: str
    guild_id: Optional[int]
    database_url: str
    log_level: str
    log_channel_id: Optional[int]
    mod_log_channel_id: Optional[int]
    welcome_channel_id: Optional[int]
    welcome_role_id: Optional[int]
    auto_role_id: Optional[int]
    staff_role_id: Optional[int]
    ticket_category_id: Optional[int]
    ticket_support_role_id: Optional[int]
    minecraft_server_ip: str
    minecraft_server_port: int
    minecraft_server_name: str
    store_url: str
    website_url: str
    vote_url: str
    discord_invite: str
    embed_color: int
    embed_footer: str

    @classmethod
    def from_env(cls) -> "Config":
        token = _get_str("DISCORD_TOKEN")
        if not token or token == "your_discord_bot_token_here":
            raise RuntimeError(
                "DISCORD_TOKEN is missing or still set to the placeholder. "
                "Copy .env.example to .env and set a real bot token."
            )

        return cls(
            discord_token=token,
            guild_id=_get_int("GUILD_ID"),
            database_url=_get_str(
                "DATABASE_URL", "sqlite+aiosqlite:///./data/stone_ffa.db"
            ),
            log_level=_get_str("LOG_LEVEL", "INFO").upper(),
            log_channel_id=_get_int("LOG_CHANNEL_ID"),
            mod_log_channel_id=_get_int("MOD_LOG_CHANNEL_ID"),
            welcome_channel_id=_get_int("WELCOME_CHANNEL_ID"),
            welcome_role_id=_get_int("WELCOME_ROLE_ID"),
            auto_role_id=_get_int("AUTO_ROLE_ID"),
            staff_role_id=_get_int("STAFF_ROLE_ID"),
            ticket_category_id=_get_int("TICKET_CATEGORY_ID"),
            ticket_support_role_id=_get_int("TICKET_SUPPORT_ROLE_ID"),
            minecraft_server_ip=_get_str(
                "MINECRAFT_SERVER_IP", "play.stoneffa.example"
            ),
            minecraft_server_port=_get_int("MINECRAFT_SERVER_PORT", 25565) or 25565,
            minecraft_server_name=_get_str("MINECRAFT_SERVER_NAME", "Stone FFA"),
            store_url=_get_str("STORE_URL", "https://store.stoneffa.example"),
            website_url=_get_str("WEBSITE_URL", "https://stoneffa.example"),
            vote_url=_get_str("VOTE_URL", "https://vote.stoneffa.example"),
            discord_invite=_get_str("DISCORD_INVITE", "https://discord.gg/your-invite"),
            embed_color=_get_color("EMBED_COLOR", 0x2F3136),
            embed_footer=_get_str("EMBED_FOOTER", "Stone FFA • Minecraft FFA"),
        )


config = Config.from_env()
