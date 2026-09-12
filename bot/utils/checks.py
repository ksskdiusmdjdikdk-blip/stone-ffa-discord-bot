"""Permission and role checks used by commands and cogs."""

from __future__ import annotations

from typing import Optional, Union

import discord
from discord import app_commands

from bot.config import config


def is_staff(member: Union[discord.Member, discord.User]) -> bool:
    """Return True if the member has the configured staff role or administrator."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    if config.staff_role_id is None:
        return (
            member.guild_permissions.manage_guild
            or member.guild_permissions.kick_members
            or member.guild_permissions.ban_members
            or member.guild_permissions.moderate_members
        )
    return any(role.id == config.staff_role_id for role in member.roles)


def staff_check():
    """app_commands check that requires staff role or administrator."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.CheckFailure("This command can only be used in a server.")
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)
        if member is None or not is_staff(member):
            raise app_commands.CheckFailure(
                "You do not have permission to use this staff command."
            )
        return True

    return app_commands.check(predicate)


def has_permissions(**perms: bool):
    """Wrapper around discord.app_commands.checks.has_permissions."""
    return app_commands.checks.has_permissions(**perms)
