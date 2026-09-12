"""Event logging: message edits/deletes and other staff-visible events."""

from __future__ import annotations

import discord
from discord.ext import commands

from bot.config import config
from bot.logger import logger
from bot.utils.embeds import info_embed, warning_embed


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        if not config.log_channel_id:
            return None
        ch = guild.get_channel(config.log_channel_id)
        return ch if isinstance(ch, discord.TextChannel) else None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        channel = self._log_channel(message.guild)
        if channel is None:
            return
        content = message.content or "[no text / embed / attachment]"
        if len(content) > 1000:
            content = content[:1000] + "…"
        embed = warning_embed(
            "Message Deleted",
            f"**Author:** {message.author.mention} (`{message.author.id}`)\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Content:**\n{content}",
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            logger.warning("Failed to log message delete")

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        if before.guild is None or before.author.bot:
            return
        if before.content == after.content:
            return
        channel = self._log_channel(before.guild)
        if channel is None:
            return
        before_c = (before.content or "")[:500]
        after_c = (after.content or "")[:500]
        embed = info_embed(
            "Message Edited",
            f"**Author:** {before.author.mention}\n"
            f"**Channel:** {before.channel.mention}\n"
            f"**Before:** {before_c or '[empty]'}\n"
            f"**After:** {after_c or '[empty]'}\n"
            f"[Jump]({after.jump_url})",
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            logger.warning("Failed to log message edit")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LoggingCog(bot))
