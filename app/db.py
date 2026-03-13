from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DB_PATH


def _ensure_db_dir() -> None:
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


def get_engine():
    _ensure_db_dir()
    return create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
