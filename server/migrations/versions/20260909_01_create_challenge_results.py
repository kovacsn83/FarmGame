"""Create Challenge results leaderboard table."""

from alembic import op
import sqlalchemy as sa


revision = "20260909_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "challenge_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=24), nullable=False),
        sa.Column("game_id", sa.String(length=36), nullable=False),
        sa.Column("challenge_type", sa.String(length=40), nullable=False),
        sa.Column("challenge_years", sa.Integer(), nullable=False),
        sa.Column("farm_value", sa.Numeric(precision=24, scale=2), nullable=False),
        sa.Column("game_version", sa.String(length=40), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "challenge_type", "challenge_years", "game_id",
            name="uq_challenge_results_challenge_game",
        ),
    )
    op.create_index(
        "ix_challenge_results_leaderboard",
        "challenge_results",
        ["challenge_type", "challenge_years", "farm_value"],
    )


def downgrade():
    op.drop_index(
        "ix_challenge_results_leaderboard", table_name="challenge_results",
    )
    op.drop_table("challenge_results")
