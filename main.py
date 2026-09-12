from fastapi import FastAPI
from socketio import ASGIApp

from database.config import create_db, engine
from database.models import Base
from io_services.events import sio
from r_services.service import r_client

from setup import update_reqs
from utils.gen_pwd import genpwd

# ============App intit================
app = FastAPI()

app.mount("/", ASGIApp(sio))


@app.on_event("startup")
async def server_init():
    print("Server starting...")
    output = await genpwd.gen_next_pwd_l()
    print(f"Done with Env pwd generation... with output: {output}")
    try:
        update_reqs.update_requirements()
    except Exception as exc:
        print(f"Failed to update requirements: {exc}")

    # return initialize_db()


def initialize_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with create_db() as db:
        print("DB Info: \n", db.info)
        db.close()
        print("Closed db successfully!!")
    r_client.reset()
    return print("Db dropped and performed redis reset!!")
