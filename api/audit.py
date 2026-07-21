import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/legal_rag")

_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    query_text: Mapped[str] = mapped_column(Text)
    doc_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieved_chunks: Mapped[Any] = mapped_column(JSON)  # [{chunk_id, score}, ...]
    final_answer: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String)
    citations: Mapped[Any] = mapped_column(JSON)  # [{doc_id, page_number, bbox, chunk_text}, ...]
    abstained: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)


async def init_audit_log() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def record_query(
    *,
    query_text: str,
    doc_id: Optional[str],
    retrieved_chunks: list[dict],
    final_answer: str,
    confidence: str,
    citations: list[dict],
    abstained: bool,
    cache_hit: bool,
) -> None:
    """Best-effort: a logging failure must never break the /query response the
    caller is waiting on, so any DB error here is caught and just logged."""
    try:
        async with _session_factory() as session:
            session.add(AuditLog(
                query_text=query_text,
                doc_id=doc_id,
                retrieved_chunks=retrieved_chunks,
                final_answer=final_answer,
                confidence=confidence,
                citations=citations,
                abstained=abstained,
                cache_hit=cache_hit,
            ))
            await session.commit()
    except Exception as e:
        logger.warning("Failed to write audit log entry (%s) — continuing without it.", e)


async def get_recent(limit: int = 50) -> list[dict]:
    async with _session_factory() as session:
        result = await session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "query_text": r.query_text,
                "doc_id": r.doc_id,
                "retrieved_chunks": r.retrieved_chunks,
                "final_answer": r.final_answer,
                "confidence": r.confidence,
                "citations": r.citations,
                "abstained": r.abstained,
                "cache_hit": r.cache_hit,
            }
            for r in rows
        ]
