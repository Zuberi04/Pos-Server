import os
from pathlib import Path
from contextlib import contextmanager
from sqlite3 import DatabaseError
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "pos_data"

DB_DIR.mkdir(parents=True, exist_ok=True)

db_path = os.getenv("DB_URL", "pos.db")

db_user = os.getenv("POSTGRES_USER", "pos")
db_pass = os.getenv("POSTGRES_PASSWORD", None)
db_name = os.getenv("POSTGRES_DB", "posdb")
path = os.path.join(
    os.path.join(os.path.dirname(os.path.abspath("../pos-db"))), db_path
)


DB_FILE = DB_DIR / "pos.db"


def join_paths(path: str):
    if path.find("sqlite") == -1:
        raise ValueError("Error, sqlite not found in path!!")
    paths = path.split("/")
    print("Paths found with values: \n", paths)

    f_path = ""

    while len(paths) > 0:
        i = 0
        part = paths[i]

        if part not in f_path:
            if part.find("sqlite") != -1:
                f_path = part + "//" + f_path
                paths.remove(part)
                i += 1
                continue
            f_path = "/" + part
            paths.remove(part)
            i += 1
            continue
        i += 1
        paths.remove(part)
        continue

    print("Path returned with value: ", f_path)
    return f_path


try:
    engine = create_engine(
        f"postgres://{db_user}:{db_pass}@postgres:5432/{db_name}", echo=True
    )
except Exception:
    print("Db path is: ", DB_FILE)
    engine = create_engine(f"sqlite:///{DB_FILE}", echo=True)  # f'sqlite:///{path}'


Session = sessionmaker(engine, autoflush=True, expire_on_commit=True)


@contextmanager
def create_db():
    db = Session()
    try:
        yield db
    except DatabaseError as e:
        raise ValueError(f"Error. generating db with value: \n\t {e}") from e
    finally:
        db.close()
