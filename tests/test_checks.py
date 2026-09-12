"""Permission helper tests (unit-level, no live Discord)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bot.utils.checks import is_staff


def test_is_staff_administrator():
    perms = SimpleNamespace(
        administrator=True,
        manage_guild=False,
        kick_members=False,
        ban_members=False,
        moderate_members=False,
    )
    member = MagicMock()
    member.guild_permissions = perms
    member.roles = []
    with patch("bot.utils.checks.discord.Member", type(member)):
        assert is_staff(member) is True


def test_is_staff_with_role():
    perms = SimpleNamespace(
        administrator=False,
        manage_guild=False,
        kick_members=False,
        ban_members=False,
        moderate_members=False,
    )
    role = SimpleNamespace(id=12345)
    member = MagicMock()
    member.guild_permissions = perms
    member.roles = [role]

    with patch("bot.utils.checks.discord.Member", type(member)):
        with patch("bot.utils.checks.config") as cfg:
            cfg.staff_role_id = 12345
            assert is_staff(member) is True

            member.roles = [SimpleNamespace(id=999)]
            assert is_staff(member) is False


def test_is_staff_fallback_permissions():
    perms = SimpleNamespace(
        administrator=False,
        manage_guild=True,
        kick_members=False,
        ban_members=False,
        moderate_members=False,
    )
    member = MagicMock()
    member.guild_permissions = perms
    member.roles = []

    with patch("bot.utils.checks.discord.Member", type(member)):
        with patch("bot.utils.checks.config") as cfg:
            cfg.staff_role_id = None
            assert is_staff(member) is True
