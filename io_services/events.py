import socketio

from io_services.event_services import IOServices
from services.auth.validate import auth_validate
from services.pos.fetch import q_fetch
from services.pos.entries.entries import entries

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    transports=["websocket", "polling"],
    async_handlers=True,
)


# initialize io services
io = IOServices(sio)


@sio.event
async def connect(sid, data):
    if not sid:
        raise ValueError("Error, no sid provided for connection!")
    print("Connected sid with value: ", sid)
    return await sio.emit(
        "connected",
        {
            "message": "Connected successfully",
            "ts": await io.timestamp(),
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    return await sio.disconnect(sid)


@sio.event
async def authenticate(sid, data: dict):
    if not data:
        return await sio.emit(
            "auth-error",
            {"error": "failed to get credentials data!", "ts": await io.timestamp()},
            to=sid,
        )
    res = await auth_validate.clean_credentials(data)
    res["ts"] = await io.timestamp()
    print("Res: ", res)
    if "id" in res:
        await sio.save_session(sid, {"user": res.id})
    return await sio.emit(
        "auth-error" if "error" in res else "authenticated", res, to=sid
    )


@sio.event
async def fetch_data(sid, data: dict):
    if not data:
        return await sio.emit("fetch-err", await io.no_data_sent(), to=sid)
    auth = await io.check_if_authenticated(data["id"], sid)
    if not isinstance(auth, str):
        auth["ts"] = await io.timestamp()
        return await sio.emit("fetch-err", auth, to=sid)
    res = await q_fetch.fetch_data(data)
    if res:
        if "columns" in res or "query" in res:
            res["ts"] = await io.timestamp()
            return await sio.emit("fetched", res, to=sid)
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
    auth = await io.check_if_authenticated(data["id"], sid)
    if not isinstance(auth, str):
        auth["ts"] = await io.timestamp()
        return await sio.emit("query-error", auth, to=sid)
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
    auth = await io.check_if_authenticated(data["id"], sid)
    if not isinstance(auth, str):
        auth["ts"] = await io.timestamp()
        return await sio.emit("entry-error", auth, to=sid)
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
    auth = await io.check_if_authenticated(data["id"], sid)
    if not isinstance(auth, str):
        auth["ts"] = await io.timestamp()
        return await sio.emit("file-error", auth, to=sid)
    res = await entries.collect_file(data)
    if res:
        res["ts"] = await io.timestamp()
        return await sio.emit(
            "filed" if not "error" in res else "file-error", res, to=sid
        )
    return await io.generic_error(sid)


@sio.event
async def accounts(sid, data: dict):
    if not data:
        return await sio.emit("accounts-err", await io.no_data_sent(), to=sid)
    auth = await io.check_if_authenticated(data["id"], sid)
    if not isinstance(auth, str):
        auth["ts"] = await io.timestamp()
        return await sio.emit("accounts-err", auth, to=sid)
    res = await q_fetch.fetch_user_profile(data, auth)
    if res:
        res["ts"] = await io.timestamp()
        return await sio.emit("accounts", res, to=sid)
    return await io.generic_error(sid)


@sio.event
async def sub_client(sid, data: dict):
    if not data:
        return await sio.emit(
            "client-err",
            {"error": "No sub-client/user data sent!!", "ts": await io.timestamp()},
            to=sid,
        )
    res = await auth_validate.clean_credentials(data)
    if res:
        res["ts"] = await io.timestamp()
        return await sio.emit("client-err" if "error" in res else "added", res, to=sid)


@sio.event
async def clear(sid, data: dict):
    sess = await io.check_if_authenticated(data["id"], sid)
    if isinstance(sess, str):
        auth = await auth_validate.clean_credentials(data)
        if "error" in auth:
            auth["ts"] = await io.timestamp()
            return await sio.emit("clear-err", auth, to=sid)
        res = await q_fetch.clear(data if "key" in data else data["id"])
        res["ts"] = await io.timestamp()
        return await sio.emit("clear-err" if "error" in res else "cleared", res, to=sid)
    sess["ts"] = await io.timestamp()
    return await sio.emit("clear-err", sess, to=sid)
