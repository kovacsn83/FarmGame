from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ChallengeResult(Base):
    __tablename__ = "challenge_results"
    __table_args__ = (
        UniqueConstraint(
            "challenge_type", "challenge_years", "game_id",
            name="uq_challenge_results_challenge_game",
        ),
        Index(
            "ix_challenge_results_leaderboard",
            "challenge_type", "challenge_years", "farm_value",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[str] = mapped_column(String(36), nullable=False)
    player_name: Mapped[str] = mapped_column(String(24), nullable=False)
    game_id: Mapped[str] = mapped_column(String(36), nullable=False)
    challenge_type: Mapped[str] = mapped_column(String(40), nullable=False)
    challenge_years: Mapped[int] = mapped_column(Integer, nullable=False)
    farm_value: Mapped[float] = mapped_column(Numeric(24, 2), nullable=False)
    game_version: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
