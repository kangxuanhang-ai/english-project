from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WordBook(Base):
    __tablename__ = "word_book"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    word: Mapped[str] = mapped_column(String)
    phonetic: Mapped[str | None] = mapped_column(String, nullable=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    pos: Mapped[str | None] = mapped_column(String, nullable=True)
    collins: Mapped[str | None] = mapped_column(String, nullable=True)
    oxford: Mapped[str | None] = mapped_column(String, nullable=True)
    tag: Mapped[str | None] = mapped_column(String, nullable=True)
    bnc: Mapped[str | None] = mapped_column(String, nullable=True)
    frq: Mapped[str | None] = mapped_column(String, nullable=True)
    exchange: Mapped[str | None] = mapped_column(Text, nullable=True)
    gk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    zk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gre: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    toefl: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ielts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cet6: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cet4: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ky: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    word_book_records = relationship("WordBookRecord", back_populates="word")

    __table_args__ = (
        Index("idx_word_book_word", "word"),
        Index("idx_word_book_tag", "tag"),
        Index("idx_word_book_word_tag", "word", "tag"),
    )


class WordBookRecord(Base):
    __tablename__ = "word_book_record"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    word_id: Mapped[str] = mapped_column(String(30), ForeignKey("word_book.id", ondelete="CASCADE"), nullable=False)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user_id: Mapped[str] = mapped_column(String(30), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="word_book_records")
    word = relationship("WordBook", back_populates="word_book_records")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_word_book_record_user_word"),
    )
