from os import getenv
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import URL, Engine, create_engine, text
from dotenv import load_dotenv

load_dotenv()


def collect_db_creds(creds: dict = {}):
    from utils.extras import clean_str, db_keys

    for k in db_keys:
        if k:
            creds[clean_str(k.split("_")[1])] = getenv(k, "")
    url = URL.create(
        "postgresql+asyncpg",
        username=creds["user"],
        password=creds["password"],
        host=creds["host"],
        database=creds["url"],
        query={"q": "?", "t": "connect_timeout=2"},
    )

    print(f"Postgres url: {url}")
    return url


def create_db_engine() -> tuple[Engine, str]:
    echo = getenv("SQL_ECHO", "false").lower() == "true"
    try:
        engine = create_async_engine(
            collect_db_creds(),
            echo=echo,
            pool_size=20,
            max_overflow=10,
            pool_recycle=800,
            pool_pre_ping=True,
        )
        with engine.connect as conn:
            conn.execute(text("SELECT 1"))
            print("Postgres db engine ONLINE!!")
            return (engine, "postgres")
    except Exception as e:
        print(f"Postgres engine OFFLINE with error: \n {str(e)}")
        from pathlib import Path

        DB_DIR = Path(__file__).resolve().parent.parent / "pos_data"
        DB_DIR.mkdir(parents=True, exist_ok=True)
        DB_FILE = DB_DIR / getenv("DB_URL", "pos.db")
        return (
            create_engine(
                f"sqlite:///{DB_FILE}",
                echo=echo,
                connect_args={"timeout": 30},
            ),
            "sqlite",
        )


from contextlib import contextmanager


def create_session():
    engine, typ = create_db_engine()
    return sessionmaker(
        bind=engine,
        class_=AsyncSession if typ == "postgres" else Session,
        autoflush=True,
        expire_on_commit=False,
    )


session = create_session()


@contextmanager
def create_db():
    db: Session = session()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
