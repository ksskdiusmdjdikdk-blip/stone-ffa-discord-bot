"""Tests for configuration loading."""

from __future__ import annotations


def test_config_requires_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.setenv("DISCORD_TOKEN", "")
    from bot.config import _get_str

    assert _get_str("DISCORD_TOKEN", "") == ""


def test_get_int_and_color(monkeypatch):
    from bot.config import _get_int, _get_color

    monkeypatch.setenv("TEST_INT", "12345")
    assert _get_int("TEST_INT") == 12345
    assert _get_int("MISSING_INT", 99) == 99
    monkeypatch.setenv("BAD_INT", "notanint")
    assert _get_int("BAD_INT") is None

    monkeypatch.setenv("COLOR_HEX", "0xFF0000")
    assert _get_color("COLOR_HEX") == 0xFF0000
    monkeypatch.setenv("COLOR_DEC", "16711680")
    assert _get_color("COLOR_DEC") == 16711680
    assert _get_color("MISSING_COLOR", 0x2F3136) == 0x2F3136


def test_embed_helpers():
    from bot.utils.embeds import (
        base_embed,
        error_embed,
        success_embed,
        warning_embed,
        info_embed,
        moderation_embed,
        ticket_embed,
        server_info_embed,
    )

    e = success_embed("Title", "Desc")
    assert "Title" in e.title
    assert e.description == "Desc"

    e2 = error_embed("Err")
    assert e2.color.value == 0xED4245

    e3 = server_info_embed()
    assert "Stone FFA" in (e3.title or "")
