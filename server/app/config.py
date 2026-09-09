import os


LOCAL_DATABASE_URL = "sqlite:///./farmgame_leaderboard.db"


def get_database_url():
    url = os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL).strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url
