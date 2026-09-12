"""Stone FFA Discord Bot entry point."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import discord
from discord.ext import commands

# Ensure project root is on sys.path when running as script
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bot.config import config
from bot.database import db
from bot.logger import logger
from bot.utils.embeds import error_embed


INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.moderation = True


class StoneFFABot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=INTENTS,
            help_command=None,
        )
        self.synced = False

    async def setup_hook(self) -> None:
        await db.init()

        # Load cogs
        cogs = [
            "bot.cogs.utility",
            "bot.cogs.minecraft",
            "bot.cogs.moderation",
            "bot.cogs.tickets",
            "bot.cogs.welcome",
            "bot.cogs.logging_cog",
        ]
        for ext in cogs:
            try:
                await self.load_extension(ext)
                logger.info("Loaded extension: %s", ext)
            except Exception:
                logger.exception("Failed to load extension %s", ext)
                raise

        # Slash command sync
        if config.guild_id:
            guild = discord.Object(id=config.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(
                "Synced %s command(s) to guild %s (development mode)",
                len(synced),
                config.guild_id,
            )
        else:
            synced = await self.tree.sync()
            logger.info("Synced %s global command(s)", len(synced))

        self.synced = True

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "?")
        activity = discord.Game(name="Stone FFA | /help")
        await self.change_presence(activity=activity)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        from discord import app_commands

        original = getattr(error, "original", error)

        if isinstance(error, app_commands.CheckFailure):
            msg = str(error) or "You do not have permission to use this command."
            embed = error_embed("Permission Denied", msg)
        elif isinstance(error, app_commands.CommandOnCooldown):
            embed = error_embed(
                "Cooldown",
                f"Try again in {error.retry_after:.1f} seconds.",
            )
        elif isinstance(error, app_commands.MissingPermissions):
            embed = error_embed(
                "Missing Permissions",
                "You lack the required Discord permissions for this command.",
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            embed = error_embed(
                "Bot Missing Permissions",
                "I am missing required permissions to run this command.",
            )
        else:
            logger.exception("Unhandled app command error: %s", error)
            embed = error_embed(
                "Something went wrong",
                "An unexpected error occurred. Staff have been notified via logs.",
            )

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            pass

        # Optional error log channel
        if config.log_channel_id and interaction.guild:
            ch = interaction.guild.get_channel(config.log_channel_id)
            if isinstance(ch, discord.TextChannel):
                try:
                    await ch.send(
                        embed=error_embed(
                            "Command Error",
                            f"`/{interaction.command.name if interaction.command else '?'}`\n"
                            f"User: {interaction.user}\n"
                            f"Error: `{type(original).__name__}: {original}`"[:1500],
                        )
                    )
                except discord.HTTPException:
                    pass

    async def close(self) -> None:
        await db.close()
        await super().close()


def main() -> None:
    bot = StoneFFABot()
    try:
        bot.run(config.discord_token, log_handler=None)
    except KeyboardInterrupt:
        logger.info("Shutting down…")
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Check DISCORD_TOKEN in .env")
        sys.exit(1)


if __name__ == "__main__":
    main()
