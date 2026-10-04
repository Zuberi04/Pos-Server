import socketio

from io_services.event_services import IOServices
from services.auth.validate import auth_validate
from services.pos.fetch import q_fetch
from services.pos.entries.entries import entries

sio = socketio.AsyncServer(
    async_mode="asgi",
    # client_manager=socketio.AsyncRedisManager("redis://localhost:6379"),
    cors_allowed_origins="*",
    transports=["websocket", "polling"],
    async_handlers=True,
    # engineio_logger=True,
)


# initialize io services
io = IOServices(sio)


@sio.event
async def connect(sid, data):
    if not sid:
        raise ValueError("Error, no sid provided for connection!")
    print("Connected sid with value: ", sid)
    await sio.emit(
        "connected",
        {
            "message": "Connected successfully",
            "ts": await io.timestamp(),
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    await sio.disconnect(sid)


@sio.event
async def authenticate(sid, data: dict):
    if not data:

        return await sio.emit("auth-error", await io.no_data_sent(), to=sid)
    res = await auth_validate.clean_credentials(data)
    res["ts"] = await io.timestamp()
    if "error" in res:
        return await sio.emit("auth-error", res, to=sid)

    return await sio.emit("authenticated", res, to=sid)


@sio.event
async def fetch_data(sid, data: dict):
    if not data:
        return await sio.emit("fetch-err", await io.no_data_sent(), to=sid)
    auth = await auth_validate.validate_authentication(data["id"])
    if auth:
        return await sio.emit("fetch-err", auth, to=sid)
    res = await q_fetch.fetch_data(data)
    if res:
        return await sio.emit(
            "fetched",
            {
                "data": res,
                "ts": await io.timestamp(),
            },
            to=sid,
        )
    return await io.generic_error(sid)


@sio.event
async def query_db(sid, data: dict):
    if not data:
        return await sio.emit("query-error", await io.no_data_sent(), to=sid)
    auth = await auth_validate.validate_authentication(data["id"])
    if auth:
        return await sio.emit("entry-error", auth, to=sio)
    res = await q_fetch.collect_query(data)
    if res:
        res["ts"] = await io.timestamp()
        return await sio.emit(
            "queried" if not "error" in res else "query-error", res, to=sid
        )
    return await io.generic_error(sid)


@sio.event
async def record_entry(sid, data: dict):
    if not data:
        return await sio.emit("entry-error", await io.no_data_sent(), to=sid)
    auth = await auth_validate.validate_authentication(data["id"])
    if auth:
        return await sio.emit("entry-error", auth, to=sio)
    res = await entries.add_entry_to_database(data)
    if res:
        return await sio.emit(
            "wrote-entry",
            {
                "message": "Succeeded in ingesting data to db!!",
                "ts": await io.timestamp(),
            },
            to=sid,
        )
    return await io.generic_error(sid)


@sio.event
async def file_entry(sid, data: dict):
    if not data:
        return await sio.emit("file-error", await io.no_data_sent(), to=sid)

    auth = await auth_validate.validate_authentication(data[0]["id"])
    if isinstance(auth, dict):
        return await sio.emit("file-error", auth, to=sid)
    res = await entries.collect_file(data)
    if res:
        res["ts"] = await io.timestamp()
        return await sio.emit(
            "filed" if not "error" in res else "file-error", res, to=sid
        )
    return await io.generic_error(sid)


@sio.event
async def me(sid, data: dict):
    auth = await auth_validate.validate_authentication(data["id"])
    if auth:
        return await sio.emit("me-error", auth, to=sid)

    res = q_fetch.fetch_user_profile(data)
    if res:
        return await sio.emit("me", {"me": res, "ts": await io.timestamp()}, to=sid)
    return await io.generic_error(sid)


@sio.event
async def collect_analysis(sid, data: dict):
    if not data:
        return await io.generic_error(sid)
    auth = await auth_validate.validate_authentication(data["id"])
    if auth:
        return await sio.emit("analysis-error", auth, to=sid)
    res = await io.collect_db_analysis(data)
    if res:
        res["ts"] = await io.timestamp()
        return await sio.emit(
            "analysis" if not "error" in res else "anlys-error", res, to=sid
        )
    return await io.generic_error(sid)
