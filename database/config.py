from os import getenv
from pathlib import Path
from sqlite3 import DatabaseError
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "pos_data"

DB_DIR.mkdir(parents=True, exist_ok=True)

db_path = getenv("DB_URL", "pos.db")
db_user = getenv("POSTGRES_USER", "pos")
db_pass = getenv("POSTGRES_PASSWORD", getenv("BACKUP_PWD", ""))

if not db_pass:
    raise ValueError(
        f"Error: failed to get config db_pass from env file with val: {db_pass}!!"
    )

try:
    engine = create_engine(
        f"postgres://{db_user}:{db_pass}@postgres:5432/{db_path}", echo=True
    )
    print("Generated Postgres DB..!!")
except Exception:
    DB_FILE = DB_DIR / db_path
    engine = create_engine(f"sqlite:///{DB_FILE}", echo=True)


Session = sessionmaker(engine, autoflush=True, expire_on_commit=True)


@contextmanager
def create_db():
    db = Session()
    try:
        yield db
    except DatabaseError as e:
        raise ValueError(f"Error: Generating db with err-value: \n\t {e}") from e
    finally:
        db.close()
