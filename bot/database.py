"""Database layer for Stone FFA Discord bot.

Uses SQLAlchemy 2.0 async with aiosqlite by default.
The DATABASE_URL can later point to PostgreSQL without rewriting application code.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    func,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bot.config import config
from bot.logger import logger


class Base(DeclarativeBase):
    pass


class WarningRecord(Base):
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    moderator_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text, default="No reason provided")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class TicketRecord(Base):
    __tablename__ = "tickets"
    __table_args__ = (UniqueConstraint("guild_id", "channel_id", name="uq_ticket_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[int] = mapped_column(BigInteger, index=True)
    moderator_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class VerificationRecord(Base):
    """Placeholder for future Minecraft account linking."""

    __tablename__ = "verifications"
    __table_args__ = (UniqueConstraint("guild_id", "user_id", name="uq_verification_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    minecraft_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    minecraft_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Database:
    """Async database helper."""

    def __init__(self, url: Optional[str] = None) -> None:
        self.url = url or config.database_url
        self.engine = create_async_engine(self.url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init(self) -> None:
        """Create tables if they do not exist."""
        if self.url.startswith("sqlite"):
            from pathlib import Path

            path_part = self.url.split("///")[-1]
            db_path = Path(path_part)
            db_path.parent.mkdir(parents=True, exist_ok=True)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized (%s)", self.url.split("://")[0])

    async def close(self) -> None:
        await self.engine.dispose()

    async def add_warning(
        self, guild_id: int, user_id: int, moderator_id: int, reason: str
    ) -> WarningRecord:
        async with self.session_factory() as session:
            record = WarningRecord(
                guild_id=guild_id,
                user_id=user_id,
                moderator_id=moderator_id,
                reason=reason or "No reason provided",
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def get_warnings(self, guild_id: int, user_id: int) -> Sequence[WarningRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(WarningRecord)
                .where(
                    WarningRecord.guild_id == guild_id,
                    WarningRecord.user_id == user_id,
                )
                .order_by(WarningRecord.created_at.desc())
            )
            return result.scalars().all()

    async def count_warnings(self, guild_id: int, user_id: int) -> int:
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count(WarningRecord.id)).where(
                    WarningRecord.guild_id == guild_id,
                    WarningRecord.user_id == user_id,
                )
            )
            return int(result.scalar_one())

    async def create_ticket(
        self, guild_id: int, channel_id: int, owner_id: int
    ) -> TicketRecord:
        async with self.session_factory() as session:
            record = TicketRecord(
                guild_id=guild_id,
                channel_id=channel_id,
                owner_id=owner_id,
                status="open",
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def get_open_ticket_by_owner(
        self, guild_id: int, owner_id: int
    ) -> Optional[TicketRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(TicketRecord).where(
                    TicketRecord.guild_id == guild_id,
                    TicketRecord.owner_id == owner_id,
                    TicketRecord.status == "open",
                )
            )
            return result.scalar_one_or_none()

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[TicketRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(TicketRecord).where(TicketRecord.channel_id == channel_id)
            )
            return result.scalar_one_or_none()

    async def close_ticket(
        self, channel_id: int, closed_by: int
    ) -> Optional[TicketRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(TicketRecord).where(TicketRecord.channel_id == channel_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return None
            record.status = "closed"
            record.closed_at = datetime.now(timezone.utc)
            record.closed_by = closed_by
            await session.commit()
            await session.refresh(record)
            return record

    async def log_moderation(
        self,
        guild_id: int,
        action: str,
        target_id: int,
        moderator_id: int,
        reason: str = "",
        extra: Optional[str] = None,
    ) -> ModerationLog:
        async with self.session_factory() as session:
            record = ModerationLog(
                guild_id=guild_id,
                action=action,
                target_id=target_id,
                moderator_id=moderator_id,
                reason=reason,
                extra=extra,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def get_verification(
        self, guild_id: int, user_id: int
    ) -> Optional[VerificationRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(VerificationRecord).where(
                    VerificationRecord.guild_id == guild_id,
                    VerificationRecord.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()

    async def set_verification_placeholder(
        self, guild_id: int, user_id: int
    ) -> VerificationRecord:
        """Mark that the user clicked verify. Real MC linking is not implemented yet."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(VerificationRecord).where(
                    VerificationRecord.guild_id == guild_id,
                    VerificationRecord.user_id == user_id,
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = VerificationRecord(
                    guild_id=guild_id,
                    user_id=user_id,
                    verified=False,
                )
                session.add(record)
            else:
                record.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(record)
            return record


db = Database()
