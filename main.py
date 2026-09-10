from fastapi import FastAPI
from socketio import ASGIApp

from database.config import create_db, engine
from database.models import Base
from io_services.events import sio
from r_services.service import r_client

from setup import update_requirements

# ============App intit================
app = FastAPI()

app.mount("/", ASGIApp(sio))


@app.on_event("startup")
async def server_init():
    print("Server starting...")

    # return initialize_db()


def initialize_db():
    update_requirements()
    Base.metadata.drop_all(engine)
    r_client.reset()
    Base.metadata.create_all(engine)
    with create_db() as db:
        db.close()
        print("Closed db successfully!!")
    return print("Db dropped and performed redis reset!!")
