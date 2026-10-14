from fastapi import FastAPI
from socketio import ASGIApp

from io_services.events import sio
from utils.gen_pwd import genpwd

# ============App intit================
app = FastAPI()

app.mount("/", ASGIApp(sio, socketio_path="socket.io"))


@app.on_event("startup")
async def server_init():
    print("Server starting...")
    await genpwd.gen_next_pwd_l()
    # return initialize_db()


def initialize_db():
    from r_services.service import r_service

    r_reset = r_service.reset_redis()
    if not r_reset:
        print("Failed to reset redis cache!!")
    try:
        from setup import update_reqs

        update_reqs.update_requirements()
    except Exception as exc:
        print(f"Failed to update requirements: {exc}")

    from database.config import create_db, engine
    from database.models import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with create_db() as db:
        db.close()
    return print("Db dropped && intialized and performed redis reset!!")
