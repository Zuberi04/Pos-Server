from fastapi import FastAPI
from socketio import ASGIApp
from pathlib import Path
from urllib.parse import quote_plus

from database.config import create_db, engine
from database.models import Base
from io_services.events import sio
from r_services.service import r_client
from utils.password import pwd

# ============App intit================
app = FastAPI()


# ==========Env path===================
env = Path(".env")

app.mount("/", ASGIApp(sio))


def reset_db():
    Base.metadata.drop_all(engine)
    r_client.reset()
    Base.metadata.create_all(engine)
    with create_db() as db:
        db.close()
        print("Closed db successfully!!")
    return print("Db dropped and performed redis reset!!")


@app.on_event("startup")
async def server_init():
    print("Server started successfully")
    p = pwd.create_password()
    if not p:
        raise ValueError("Error, failed to get p!!")

    print("Is env file: ", env.is_file())
    write = [
        "POSTGRES_USER=pos",
        f"POSTGRES_PASSWORD={quote_plus(pwd.create_password())}",
        "POSTGRES_DB=posdb",
    ]
    for w in write:
        wrote = env.write_text(w)
        if not wrote:
            raise ValueError("Error, failed to write to env!!")
        print("Wrote with value: ", wrote)
        continue

    # return reset_db()
