"""Minecraft server status and player lookup service.

Uses the public mcstatus-compatible HTTP endpoints via aiohttp.
No blocking calls; all I/O is async.

Status is obtained from the free public API at api.mcsrvstat.us
(documented at https://api.mcsrvstat.us/). This avoids requiring
an extra native dependency and works for both Java and Bedrock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import aiohttp

from bot.config import config
from bot.logger import logger


@dataclass
class ServerStatus:
    online: bool
    ip: str
    port: int
    hostname: Optional[str] = None
    players_online: int = 0
    players_max: int = 0
    version: Optional[str] = None
    motd: Optional[str] = None
    latency_ms: Optional[float] = None
    software: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PlayerInfo:
    """Placeholder for future player lookups (NameMC, Mojang, server plugin, etc.)."""

    username: str
    uuid: Optional[str] = None
    online: Optional[bool] = None
    found: bool = False
    extra: Optional[dict[str, Any]] = None


class MinecraftService:
    """Async Minecraft status and player information helper."""

    STATUS_URL = "https://api.mcsrvstat.us/3/{host}"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: float = 8.0,
    ) -> None:
        self.host = host or config.minecraft_server_ip
        self.port = port or config.minecraft_server_port
        self.timeout = timeout

    async def get_status(self) -> ServerStatus:
        """Query public status API for the configured server."""
        query_host = self.host
        if self.port and self.port != 25565:
            query_host = f"{self.host}:{self.port}"

        url = self.STATUS_URL.format(host=query_host)
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning("Minecraft status API returned %s", resp.status)
                        return ServerStatus(
                            online=False,
                            ip=self.host,
                            port=self.port,
                            error=f"Status API returned HTTP {resp.status}",
                        )
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            logger.warning("Minecraft status request failed: %s", exc)
            return ServerStatus(
                online=False,
                ip=self.host,
                port=self.port,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error fetching Minecraft status")
            return ServerStatus(
                online=False,
                ip=self.host,
                port=self.port,
                error=str(exc),
            )

        online = bool(data.get("online"))
        players = data.get("players") or {}
        version = data.get("version")
        if isinstance(version, dict):
            version = version.get("name") or str(version)

        motd = None
        motd_data = data.get("motd")
        if isinstance(motd_data, dict):
            clean = motd_data.get("clean")
            if isinstance(clean, list):
                motd = " ".join(clean)
            elif isinstance(clean, str):
                motd = clean

        return ServerStatus(
            online=online,
            ip=data.get("ip") or self.host,
            port=int(data.get("port") or self.port),
            hostname=data.get("hostname"),
            players_online=int(players.get("online") or 0),
            players_max=int(players.get("max") or 0),
            version=str(version) if version else None,
            motd=motd,
            software=data.get("software"),
            latency_ms=None,
            error=None if online else "Server appears offline",
        )

    async def get_player(self, username: str) -> PlayerInfo:
        """
        Lookup a Minecraft player.

        Currently returns a clean placeholder. Real integration (Mojang API,
        server plugin, Hypixel-style, or custom backend) can be added later
        without changing command code.
        """
        username = username.strip()
        if not username or len(username) > 16:
            return PlayerInfo(username=username, found=False)

        return PlayerInfo(
            username=username,
            found=False,
            extra={
                "note": "Minecraft player lookup is not connected yet. "
                "This command is ready for integration."
            },
        )


minecraft_service = MinecraftService()
