from os import getenv
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import URL, Engine, create_engine
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()


def collect_db_creds(creds: dict = {}):
    from utils.extras import clean_str, db_keys

    for k in db_keys:
        if k:
            creds[clean_str(k.split("_")[1])] = getenv(k, "")
    url = URL.create(
        "postgresql+psycopg2",
        username=creds["user"],
        password=creds["password"],
        host=creds["host"],
        database=creds["url"],
    )
    return url


@lru_cache(maxsize=2)
def create_db_engine(typ: str) -> Engine:
    echo = getenv("SQL_ECHO", "false").lower() == "true"
    if typ != "postgres":
        print("Creating backup sqlalchemy engine!!")
        if typ not in ("sql", "sqlite"):
            raise ValueError(f"Unsupporrted type {typ} of db engine")
        from pathlib import Path

        DB_DIR = Path(__file__).resolve().parent.parent / "pos_data"
        DB_DIR.mkdir(parents=True, exist_ok=True)
        DB_FILE = DB_DIR / getenv("DB_URL", "pos.db")
        return create_engine(
            f"sqlite:///{DB_FILE}",
            echo=echo,
            connect_args={"timeout": 30},
        )
    return create_engine(
        collect_db_creds(),
        echo=echo,
        pool_size=20,
        max_overflow=10,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


from contextlib import contextmanager


@lru_cache(maxsize=2)
def create_session(typ: str = "postgres"):
    return sessionmaker(
        bind=create_db_engine(typ), autoflush=True, expire_on_commit=False
    )


@contextmanager
def create_db(flag: str = None):
    db: Session = create_session(flag if flag else getenv("DB_ENGINE", "postgres"))()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
