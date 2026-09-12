"""Database operation tests using a temporary SQLite file."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from bot.database import Database


@pytest_asyncio.fixture
async def database(tmp_path: Path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    db = Database(url)
    await db.init()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_warnings_cycle(database: Database):
    rec = await database.add_warning(1, 100, 200, "test reason")
    assert rec.id is not None
    assert rec.reason == "test reason"

    count = await database.count_warnings(1, 100)
    assert count == 1

    warnings = await database.get_warnings(1, 100)
    assert len(warnings) == 1
    assert warnings[0].moderator_id == 200


@pytest.mark.asyncio
async def test_tickets_cycle(database: Database):
    t = await database.create_ticket(1, 999, 100)
    assert t.status == "open"

    open_t = await database.get_open_ticket_by_owner(1, 100)
    assert open_t is not None
    assert open_t.channel_id == 999

    by_ch = await database.get_ticket_by_channel(999)
    assert by_ch is not None

    closed = await database.close_ticket(999, 200)
    assert closed is not None
    assert closed.status == "closed"
    assert closed.closed_by == 200

    open_again = await database.get_open_ticket_by_owner(1, 100)
    assert open_again is None


@pytest.mark.asyncio
async def test_moderation_log(database: Database):
    log = await database.log_moderation(1, "kick", 100, 200, "reason", "extra")
    assert log.action == "kick"
    assert log.extra == "extra"


@pytest.mark.asyncio
async def test_verification_placeholder(database: Database):
    rec = await database.set_verification_placeholder(1, 50)
    assert rec.verified is False
    again = await database.get_verification(1, 50)
    assert again is not None
    assert again.user_id == 50
