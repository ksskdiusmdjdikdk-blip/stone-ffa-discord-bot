"""Minecraft-related commands (status, player lookup)."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config
from bot.services.minecraft import minecraft_service
from bot.utils.embeds import base_embed, error_embed, info_embed


class Minecraft(commands.Cog):
    """Minecraft server status and player information."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="status", description="Check Stone FFA Minecraft server status")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        try:
            st = await minecraft_service.get_status()
        except Exception:  # noqa: BLE001
            embed = error_embed(
                "Status Unavailable",
                "Could not reach the Minecraft status service. Try again later.",
            )
            await interaction.followup.send(embed=embed)
            return

        if st.online:
            embed = base_embed(
                title="🟢 Stone FFA – Online",
                description=st.motd or "Server is online.",
                color=0x57F287,
            )
            embed.add_field(
                name="Players",
                value=f"{st.players_online}/{st.players_max}",
                inline=True,
            )
            if st.version:
                embed.add_field(name="Version", value=str(st.version), inline=True)
            if st.software:
                embed.add_field(name="Software", value=str(st.software), inline=True)
            embed.add_field(
                name="Address",
                value=f"`{config.minecraft_server_ip}:{config.minecraft_server_port}`",
                inline=False,
            )
        else:
            embed = base_embed(
                title="🔴 Stone FFA – Offline",
                description=st.error or "Server appears offline.",
                color=0xED4245,
            )
            embed.add_field(
                name="Address",
                value=f"`{config.minecraft_server_ip}:{config.minecraft_server_port}`",
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="player", description="Look up a Minecraft player (placeholder)")
    @app_commands.describe(username="Minecraft username")
    async def player(self, interaction: discord.Interaction, username: str) -> None:
        await interaction.response.defer(thinking=True)
        info = await minecraft_service.get_player(username)

        embed = info_embed(
            f"Player: {info.username}",
            "Minecraft player lookup is prepared for future integration.\n"
            "No live player data is available yet.",
        )
        if info.extra and info.extra.get("note"):
            embed.add_field(name="Note", value=info.extra["note"], inline=False)

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Minecraft(bot))
