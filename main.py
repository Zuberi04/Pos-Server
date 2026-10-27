import signal
import logging
from os import kill, getpid
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.background import BackgroundTask
from socketio import ASGIApp
from io_services.events import sio
from database.config import create_db, create_db_engine
from database.models import Base

# ============App init================

app = FastAPI(title="Archie's Pos", debug=True)
logger = logging.getLogger("security")


@app.get("/", response_class=HTMLResponse)
async def homepage():
    return "<!doctype html><html><head><title>Archie's POS</title></head><body><h1>Archie's POS server is online.</h1></body></html>"


app.mount("/", ASGIApp(sio, socketio_path="socket.io"))


@app.on_event("startup")
async def server_init():
    from utils.gen_pwd import genpwd

    await genpwd.gen_next_pwd_l()
    """try:
        from setup import update_reqs
        update_reqs.audit_installed_pkgs()
    except Exception as exc:
        print(f"Failed to update requirements.txt with error:\n {exc}")"""
    return await initialize_db()


@app.on_event("shutdown")
async def shut_down_services():
    with create_db() as db:
        db.close()
        return print("App shutting down after success closing db connection!!")


async def initialize_db(flag: str = "start"):
    from r_services.service import r_service

    engine, typ = create_db_engine()
    if flag == "reset":
        try:
            r = r_service.reset_redis().decode("utf-8")
        except Exception:
            r = r_service.reset_redis()
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with create_db() as db:
            db.close()
            return print(
                f"Db dropped && intialized with type: {typ.capitalize()} && redis-reset? {r}!!"
            )
    return print(
        f"[DB-CONN] verified successfully with engine type: {typ.capitalize()}"
    )


def emergeny_halt():
    """Triggers clean ASGI shutdown via OS signal"""
    logger.critical("SYSTEM HALTED SCRIPT RECONSTRUCTION TRIGGERED")
    kill(getpid(), signal.SIGTERM)


@app.post("/report_breach")
async def report_attack():
    logger.error("Active attack vendor detected! Initiating emergency lock down")
    BackgroundTask(emergeny_halt)

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="system undergoing critical isolation.",
        headers={"Retry-After": "3600"},
    )


from sqlalchemy.exc import OperationalError


@app.exception_handler(OperationalError)
async def panic_handler(request: Request, exc: OperationalError):
    print(f"Critical db engine failure with error: \n {exc}")
    kill(getpid(), signal.SIGTERM)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database unvailable. Service isolating till fix is achieved"
        },
        headers=request.headers,
    )
