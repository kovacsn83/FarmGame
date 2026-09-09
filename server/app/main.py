import logging
from contextlib import asynccontextmanager
from datetime import timezone

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .database import create_database_engine, create_session_factory
from .models import ChallengeResult
from .schemas import (
    ChallengeSubmission, LeaderboardEntry, LeaderboardResponse,
    SubmissionResponse,
)


CHALLENGE_TYPE = "ten_year"
CHALLENGE_YEARS = 10
logger = logging.getLogger("farmgame.leaderboard")


def error_response(status_code, code, message):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def as_utc(value):
    """Normalize timestamps; SQLite may return timezone-naive values."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_app(database_url=None):
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app):
        logger.info("FarmGame leaderboard API starting")
        try:
            with engine.connect() as connection:
                connection.execute(select(1))
            logger.info("Database connection ready")
        except SQLAlchemyError:
            logger.exception("Database connection failed at startup")
        yield
        engine.dispose()

    app = FastAPI(
        title="FarmGame Challenge API", version="1.0.0", lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, error):
        logger.warning("Challenge API request validation failed")
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "The request body is invalid.",
                    "details": [
                        {"location": list(item["loc"]), "message": item["msg"],
                         "type": item["type"]}
                        for item in error.errors()
                    ],
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, _error):
        logger.error("Unexpected Challenge API error", exc_info=_error)
        return error_response(
            500, "internal_server_error", "An unexpected server error occurred.",
        )

    @app.get("/health")
    def health(session: Session = Depends(get_session)):
        try:
            session.execute(select(1))
        except SQLAlchemyError:
            logger.exception("Database health check failed")
            return error_response(
                503, "database_unavailable", "The database is unavailable.",
            )
        return {"status": "ok", "database": "ok"}

    @app.post(
        "/api/v1/challenges/ten-year/submit",
        response_model=SubmissionResponse,
        status_code=201,
    )
    def submit_score(
            submission: ChallengeSubmission,
            session: Session = Depends(get_session)):
        record = ChallengeResult(
            player_id=str(submission.player_id),
            player_name=submission.player_name,
            game_id=str(submission.game_id),
            challenge_type=CHALLENGE_TYPE,
            challenge_years=CHALLENGE_YEARS,
            farm_value=submission.farm_value,
            game_version=submission.game_version,
            completed_at=as_utc(submission.completed_at),
        )
        session.add(record)
        try:
            session.commit()
            session.refresh(record)
        except IntegrityError:
            session.rollback()
            logger.info("Duplicate Challenge submission rejected")
            return error_response(
                409, "challenge_result_already_submitted",
                "This game already submitted a result for this challenge.",
            )
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Challenge submission database error")
            return error_response(
                503, "database_unavailable",
                "The result could not be stored.",
            )

        ranked = select(
            ChallengeResult.id.label("result_id"),
            func.row_number().over(order_by=(
                ChallengeResult.farm_value.desc(),
                ChallengeResult.completed_at.asc(),
                ChallengeResult.submitted_at.asc(),
                ChallengeResult.id.asc(),
            )).label("rank"),
        ).where(
            ChallengeResult.challenge_type == CHALLENGE_TYPE,
            ChallengeResult.challenge_years == CHALLENGE_YEARS,
        ).subquery()
        rank = session.scalar(select(ranked.c.rank).where(
            ranked.c.result_id == record.id,
        ))
        logger.info("Challenge submission accepted (result_id=%s)", record.id)
        return SubmissionResponse(
            status="accepted", result_id=record.id, game_id=record.game_id,
            farm_value=float(record.farm_value), rank=rank,
        )

    @app.get(
        "/api/v1/challenges/ten-year/leaderboard",
        response_model=LeaderboardResponse,
    )
    def leaderboard(
            limit: int = Query(default=10, ge=1, le=100),
            game_version: str | None = Query(default=None, min_length=1, max_length=40),
            session: Session = Depends(get_session)):
        query = select(ChallengeResult).where(
            ChallengeResult.challenge_type == CHALLENGE_TYPE,
            ChallengeResult.challenge_years == CHALLENGE_YEARS,
        )
        if game_version is not None:
            query = query.where(ChallengeResult.game_version == game_version)
        records = session.scalars(query.order_by(
            ChallengeResult.farm_value.desc(),
            ChallengeResult.completed_at.asc(),
            ChallengeResult.submitted_at.asc(),
            ChallengeResult.id.asc(),
        ).limit(limit)).all()
        return LeaderboardResponse(
            challenge=CHALLENGE_TYPE,
            challenge_years=CHALLENGE_YEARS,
            results=[LeaderboardEntry(
                rank=index,
                player_name=record.player_name,
                farm_value=float(record.farm_value),
                game_version=record.game_version,
                completed_at=as_utc(record.completed_at),
            ) for index, record in enumerate(records, start=1)],
        )

    return app


app = create_app()
