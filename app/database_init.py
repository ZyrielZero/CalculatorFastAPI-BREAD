from app.database import Base, engine

# Import the models package so every model registers on Base.metadata
# before create_all runs — user and calculation both live there.
import app.models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    Base.metadata.drop_all(bind=engine)