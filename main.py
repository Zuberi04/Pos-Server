import signal
import logging
from os import kill, getpid
from typing import Any
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.background import BackgroundTask
from socketio import ASGIApp

from io_services.events import sio
from database.config import create_db, create_session, create_db_engine
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
    try:
        from setup import update_reqs

        update_reqs.audit_installed_pkgs()
    except Exception as exc:
        print(f"Failed to update requirements: {exc}")
    init = await initialize_db("reset")
    if init:
        return print(
            init
            if init and not isinstance(init, bytes)
            else init.decode("utf-8", errors="replace")
        )


@app.on_event("shutdown")
async def shut_down_services():
    with create_db() as db:
        db.close()


async def initialize_db(flag: str = "start"):

    from r_services.service import r_service

    try:
        typ = "postgres"
        engine = create_db_engine(typ)
        test_db_active(engine)
    except Exception:
        typ = "sqlite"
        engine = create_db_engine(typ)
        test_db_active(engine, typ)
    await write_engine_to_env(f"DB_ENGINE={typ}")
    if flag == "reset":
        r_service.reset_redis()
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with create_db() as db:
            db.close()
            return print("Db dropped && intialized and performed redis reset!!")
    return print("[DB-CONN] verified successfully")


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


def test_db_active(engine: Any, flag: str = None):
    print(f"Flag found with value: {flag}")
    Base.metadata.reflect(engine)
    with create_db(flag) as db:
        db.info.update({"active": True})
        print("Db session info: ", db.info)
        return db.close()


async def write_engine_to_env(typ: str):
    print("Writing db engine to env!!")
    from pathlib import Path

    p = Path(".env")
    if not p.is_file():
        raise ValueError("Error env not found!!")
    print("Starting read of db engine!!")
    with p.open("a") as w:
        data: list = None
        with p.open("r") as r:
            data = [x.replace("\n", "") for x in r.readlines()]
        if not data:
            raise ValueError("Error no data in env!!")
        for d in data:
            if d.split("=")[0] == typ.split("=")[0]:
                data.remove(d)
        data.append(typ)
        print("Data found with value: \n", data)
        for d in data:
            if not data.index(d):
                p.write_text(f"{d}\n")
            else:
                w.write(f"{d}\n")
