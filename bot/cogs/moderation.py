"""Staff moderation commands for Stone FFA."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config
from bot.database import db
from bot.logger import logger
from bot.utils.checks import is_staff, staff_check
from bot.utils.embeds import (
    error_embed,
    info_embed,
    moderation_embed,
    success_embed,
    warning_embed,
)


class Moderation(commands.Cog):
    """Warn, mute, kick, ban, timeout, purge, slowmode."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _mod_log(
        self,
        guild: discord.Guild,
        action: str,
        target: discord.abc.User,
        moderator: discord.abc.User,
        reason: str,
        extra: str = "",
    ) -> None:
        await db.log_moderation(
            guild_id=guild.id,
            action=action,
            target_id=target.id,
            moderator_id=moderator.id,
            reason=reason,
            extra=extra or None,
        )
        channel_id = config.mod_log_channel_id or config.log_channel_id
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        embed = moderation_embed(
            f"{action.title()}",
            f"**Target:** {target.mention} (`{target.id}`)\n"
            f"**Moderator:** {moderator.mention}\n"
            f"**Reason:** {reason or 'No reason provided'}"
            + (f"\n{extra}" if extra else ""),
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            logger.warning("Failed to send mod log to channel %s", channel_id)

    def _can_moderate(
        self, actor: discord.Member, target: discord.Member
    ) -> tuple[bool, str]:
        if actor.id == target.id:
            return False, "You cannot moderate yourself."
        if target.id == actor.guild.owner_id:
            return False, "You cannot moderate the server owner."
        if target.top_role >= actor.top_role and actor.id != actor.guild.owner_id:
            return False, "You cannot moderate a member with an equal or higher role."
        if target.guild_permissions.administrator and not actor.guild_permissions.administrator:
            return False, "You cannot moderate an administrator."
        return True, ""

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @staff_check()
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                embed=error_embed("Error", "Invalid context."), ephemeral=True
            )
            return
        ok, msg = self._can_moderate(interaction.user, member)
        if not ok:
            await interaction.response.send_message(embed=error_embed("Denied", msg), ephemeral=True)
            return

        record = await db.add_warning(
            interaction.guild_id, member.id, interaction.user.id, reason
        )
        count = await db.count_warnings(interaction.guild_id, member.id)

        embed = warning_embed(
            "Member Warned",
            f"{member.mention} has been warned.\n"
            f"**Reason:** {reason}\n"
            f"**Total warnings:** {count}",
        )
        await interaction.response.send_message(embed=embed)
        await self._mod_log(
            interaction.guild, "warn", member, interaction.user, reason, f"Warning #{record.id}"
        )

        try:
            await member.send(
                embed=warning_embed(
                    f"Warned on {interaction.guild.name}",
                    f"**Reason:** {reason}\n**Total warnings:** {count}",
                )
            )
        except discord.HTTPException:
            pass

    @app_commands.command(name="warnings", description="View warnings for a member")
    @app_commands.describe(member="Member to check")
    @staff_check()
    async def warnings(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        records = await db.get_warnings(interaction.guild_id, member.id)
        if not records:
            await interaction.response.send_message(
                embed=info_embed("Warnings", f"{member.mention} has no warnings."),
                ephemeral=True,
            )
            return
        lines = [
            f"`#{r.id}` <t:{int(r.created_at.timestamp())}:R> — {r.reason}"
            for r in records[:15]
        ]
        embed = moderation_embed(
            f"Warnings for {member.display_name}",
            "\n".join(lines) + (f"\n… and {len(records) - 15} more" if len(records) > 15 else ""),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(member="Member to kick", reason="Reason")
    @app_commands.checks.has_permissions(kick_members=True)
    @staff_check()
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        ok, msg = self._can_moderate(interaction.user, member)
        if not ok:
            await interaction.response.send_message(embed=error_embed("Denied", msg), ephemeral=True)
            return
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.response.send_message(
                embed=error_embed("Missing Permission", "I need Kick Members."), ephemeral=True
            )
            return

        try:
            await member.kick(reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Failed", "I cannot kick that member."), ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed("Member Kicked", f"{member} was kicked.\n**Reason:** {reason}")
        )
        await self._mod_log(interaction.guild, "kick", member, interaction.user, reason)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(
        member="Member to ban",
        reason="Reason",
        delete_message_days="Delete message history (0-7 days)",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    @staff_check()
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        ok, msg = self._can_moderate(interaction.user, member)
        if not ok:
            await interaction.response.send_message(embed=error_embed("Denied", msg), ephemeral=True)
            return
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(
                embed=error_embed("Missing Permission", "I need Ban Members."), ephemeral=True
            )
            return

        try:
            await member.ban(
                reason=f"{interaction.user}: {reason}",
                delete_message_seconds=delete_message_days * 86400,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Failed", "I cannot ban that member."), ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed("Member Banned", f"{member} was banned.\n**Reason:** {reason}")
        )
        await self._mod_log(interaction.guild, "ban", member, interaction.user, reason)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="Discord user ID to unban", reason="Reason")
    @app_commands.checks.has_permissions(ban_members=True)
    @staff_check()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "No reason provided",
    ) -> None:
        try:
            uid = int(user_id)
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("Invalid ID", "Provide a numeric Discord user ID."),
                ephemeral=True,
            )
            return

        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=f"{interaction.user}: {reason}")
        except discord.NotFound:
            await interaction.response.send_message(
                embed=error_embed("Not Found", "That user is not banned or does not exist."),
                ephemeral=True,
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Failed", "I cannot unban that user."), ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed("User Unbanned", f"{user} (`{uid}`) was unbanned.")
        )
        await self._mod_log(interaction.guild, "unban", user, interaction.user, reason)

    @app_commands.command(name="timeout", description="Timeout (mute) a member")
    @app_commands.describe(
        member="Member to timeout",
        minutes="Duration in minutes (1–40320)",
        reason="Reason",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    @staff_check()
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "No reason provided",
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return
        ok, msg = self._can_moderate(interaction.user, member)
        if not ok:
            await interaction.response.send_message(embed=error_embed("Denied", msg), ephemeral=True)
            return

        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Failed", "I cannot timeout that member."), ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed(
                "Member Timed Out",
                f"{member.mention} timed out for **{minutes}** minutes.\n**Reason:** {reason}",
            )
        )
        await self._mod_log(
            interaction.guild,
            "timeout",
            member,
            interaction.user,
            reason,
            f"Duration: {minutes}m",
        )

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.describe(member="Member to untimeout", reason="Reason")
    @app_commands.checks.has_permissions(moderate_members=True)
    @staff_check()
    async def untimeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        try:
            await member.timeout(None, reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Failed", "I cannot remove that timeout."), ephemeral=True
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Failed", str(exc)), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=success_embed("Timeout Removed", f"Timeout removed from {member.mention}.")
        )
        await self._mod_log(interaction.guild, "untimeout", member, interaction.user, reason)

    @app_commands.command(name="mute", description="Alias for /timeout")
    @app_commands.describe(member="Member", minutes="Minutes", reason="Reason")
    @app_commands.checks.has_permissions(moderate_members=True)
    @staff_check()
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320] = 60,
        reason: str = "No reason provided",
    ) -> None:
        await self.timeout.callback(self, interaction, member, minutes, reason)

    @app_commands.command(name="unmute", description="Alias for /untimeout")
    @app_commands.describe(member="Member", reason="Reason")
    @app_commands.checks.has_permissions(moderate_members=True)
    @staff_check()
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        await self.untimeout.callback(self, interaction, member, reason)

    @app_commands.command(name="purge", description="Delete a number of messages")
    @app_commands.describe(amount="Number of messages to delete (1–100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    @staff_check()
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=error_embed("Invalid Channel", "Purge only works in text channels."),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            embed=success_embed("Purged", f"Deleted **{len(deleted)}** messages."),
            ephemeral=True,
        )
        await self._mod_log(
            interaction.guild,
            "purge",
            interaction.user,
            interaction.user,
            f"Deleted {len(deleted)} messages in #{interaction.channel.name}",
        )

    @app_commands.command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable, max 21600)")
    @app_commands.checks.has_permissions(manage_channels=True)
    @staff_check()
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=error_embed("Invalid Channel", "Only text channels support slowmode."),
                ephemeral=True,
            )
            return
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Failed", "I cannot edit this channel."), ephemeral=True
            )
            return
        msg = "Slowmode disabled." if seconds == 0 else f"Slowmode set to **{seconds}** seconds."
        await interaction.response.send_message(embed=success_embed("Slowmode", msg))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
