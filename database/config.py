from os import getenv
from sqlite3 import DatabaseError

from pathlib import Path
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from dotenv import load_dotenv

from utils.password import pwd

load_dotenv()


def load_envs():
    env = Path(".env")
    if not env.is_file:
        raise FileNotFoundError("Error, .env file is missing from root dir!!")
    found = 0
    with env.open("r") as r:
        data = r.readlines()
        if data:
            for d in data:
                if d.find("USER") != -1 or d.find("PASS") != -1 or d.find("URL") != -1:
                    found += 1

    if found < 3:
        env.write_text(f"""\n
            POSTGRES_USER=archie_pos \n
            POSTGRES_PASSWORD={quote_plus(pwd.password())} \n
            DB_URL=pos.db
            """)
        return print("Wrote to env with upd file size of: ", env.stat.st_size())
    return print(f"Found keys in env file with count: {found}")


load_envs()


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "pos_data"

DB_DIR.mkdir(parents=True, exist_ok=True)

db_path = getenv("DB_URL", "pos.db")
db_user = getenv("POSTGRES_USER", "pos")
db_pass = getenv("POSTGRES_PASSWORD", "BACKUP_PASS")

if not db_pass:
    raise ValueError(
        f"Error: failed to get config db_pass from env file with val: {db_pass}!!"
    )

try:
    engine = create_engine(
        f"postgres://{db_user}:{db_pass}@postgres:5432/{db_path}", echo=True
    )
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
