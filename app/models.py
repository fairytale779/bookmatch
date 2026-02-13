from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Text, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    contents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    isbn: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    translators: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sale_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
