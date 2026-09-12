"""Reusable embed builders with consistent Stone FFA branding."""

from __future__ import annotations

from typing import Optional

import discord

from bot.config import config


def base_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[int] = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color if color is not None else config.embed_color,
    )
    embed.set_footer(text=config.embed_footer)
    return embed


def success_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(title=f"✅ {title}", description=description, color=0x57F287)


def error_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(title=f"❌ {title}", description=description, color=0xED4245)


def warning_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(title=f"⚠️ {title}", description=description, color=0xFEE75C)


def info_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(title=f"ℹ️ {title}", description=description, color=0x5865F2)


def moderation_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(title=f"🛡️ {title}", description=description, color=0xEB459E)


def ticket_embed(title: str, description: str = "") -> discord.Embed:
    return base_embed(title=f"🎫 {title}", description=description, color=0x57F287)


def server_info_embed() -> discord.Embed:
    embed = base_embed(
        title="⚔️ Stone FFA",
        description="Competitive Minecraft Free-For-All server.",
    )
    embed.add_field(name="Server IP", value=f"`{config.minecraft_server_ip}`", inline=True)
    embed.add_field(name="Port", value=f"`{config.minecraft_server_port}`", inline=True)
    embed.add_field(name="Name", value=config.minecraft_server_name, inline=True)
    embed.add_field(name="Website", value=config.website_url, inline=False)
    embed.add_field(name="Store", value=config.store_url, inline=True)
    embed.add_field(name="Vote", value=config.vote_url, inline=True)
    return embed
