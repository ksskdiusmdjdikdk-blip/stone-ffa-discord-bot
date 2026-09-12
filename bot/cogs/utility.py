"""Utility and information commands for Stone FFA."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config
from bot.utils.embeds import base_embed, error_embed, info_embed, server_info_embed


class Utility(commands.Cog):
    """Public information and help commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="server", description="Show Stone FFA server information")
    async def server(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=server_info_embed())

    @app_commands.command(name="ip", description="Show the Minecraft server IP")
    async def ip(self, interaction: discord.Interaction) -> None:
        embed = info_embed(
            "Server IP",
            f"**IP:** `{config.minecraft_server_ip}`\n"
            f"**Port:** `{config.minecraft_server_port}`",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="store", description="Open the Stone FFA store")
    async def store(self, interaction: discord.Interaction) -> None:
        embed = info_embed("Store", f"[Visit the store]({config.store_url})")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vote", description="Vote for Stone FFA")
    async def vote(self, interaction: discord.Interaction) -> None:
        embed = info_embed("Vote", f"[Vote for the server]({config.vote_url})")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="website", description="Stone FFA website")
    async def website(self, interaction: discord.Interaction) -> None:
        embed = info_embed("Website", f"[Visit the website]({config.website_url})")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="discord", description="Discord invite link")
    async def discord_invite(self, interaction: discord.Interaction) -> None:
        embed = info_embed("Discord", f"[Join the community]({config.discord_invite})")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="List available Stone FFA bot commands")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        embed = base_embed(
            title="Stone FFA Help",
            description="Slash commands available on this server.",
        )
        embed.add_field(
            name="Information",
            value=(
                "`/server` – Server info\n"
                "`/ip` – Server IP\n"
                "`/store` `/vote` `/website` `/discord`\n"
                "`/status` – Live Minecraft status\n"
                "`/player <username>` – Player info (placeholder)"
            ),
            inline=False,
        )
        embed.add_field(
            name="Tickets",
            value="Use the ticket panel button or `/ticket` (if available).",
            inline=False,
        )
        embed.add_field(
            name="Moderation (staff)",
            value=(
                "`/warn` `/mute` `/unmute` `/kick` `/ban` `/unban`\n"
                "`/timeout` `/untimeout` `/purge` `/slowmode`"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
