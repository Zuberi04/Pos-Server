import datetime
from typing import Any

from numpy import isin

from database.config import create_db
from utils.extras import clean_data, run_in_thread_pool, MODELS, TS_FLAGS, clean_str


class ReadStatements:
    def __init__(self):
        self.ts_flags = TS_FLAGS

    @run_in_thread_pool
    async def read_stmt(
        self,
        model: Any,
        query: Any = None,
        column: str = None,
        flag: str = None,
        stmts: Any = None,
    ):
        from sqlalchemy import select

        with create_db() as db:
            if not query and not column:
                stmts = db.scalars(select(model)).all()
            else:
                for col in model.__table__.c:
                    if column and col.key == column:
                        return db.scalars(select(col).select_from(model.__table__))
                    elif flag:
                        return db.scalars(
                            select(model).where(
                                col.type.python_type == type(query) and col == query
                                if col.key.find("id") == -1
                                else col == await self.convert_id(query)
                            )
                        ).first()
                    else:
                        stmts = db.scalars(
                            select(model).where(
                                col.type.python_type == type(query) and col == query
                                if col.key.find("id") == -1
                                else col == await self.convert_id(query)
                            )
                        ).all()
                    if stmts:
                        break
            if not stmts:
                return None
            result = []
            for stmt in stmts:
                result.append(await self.read_stmt_to_dict(stmt))
            return result if len(result) > 1 else result[0]

    @staticmethod
    @run_in_thread_pool
    def read_stmt_to_dict(stmt: Any):
        if stmt:
            if not isinstance(stmt, dict):
                from sqlalchemy import inspect

                try:
                    return {
                        c.key: getattr(stmt, c.key)
                        for c in inspect(stmt, raiseerr=ValueError).mapper.column_attrs
                    }
                except ValueError:
                    return {
                        clean_str(col.key): getattr(stmt, col.key, None)
                        for col in stmt.__table__.c
                    }
            return stmt
        return None

    @staticmethod
    @run_in_thread_pool
    def convert_id(id: Any):
        from database.models import GUID

        return GUID().process_result_value(id)

    @run_in_thread_pool
    async def write_items_to_db(self, model: Any, data: dict):
        mod = model()
        print("Inserting data with values: \n\t", data)
        with create_db() as db:
            for col in mod.__table__.c:
                if col.key in data and col.key != "id":
                    try:
                        if isinstance(data[col.key], col.type.python_type):
                            setattr(mod, col.key, data[col.key])
                    except NotImplementedError:
                        setattr(mod, col.key, data[col.key])
            db.add(mod)
            db.commit()
            return await self.update_audits(
                model, data, await self.read_stmt_to_dict(mod)
            )

    @run_in_thread_pool
    async def update_audits(
        self, model: Any, data: dict, record: dict, prev: dict = None
    ):
        if isinstance(model, str):
            from services.pos.audits import audit_log

            if not "user_id" in data:
                from utils.rel import upd

                data["user_id"] = await upd.find_user_id(record)
                if not data["user_id"]:
                    raise ValueError(
                        f"Failed to find user id for record: \n\t {record}"
                    )
            await audit_log.add_audit_log(record, data["user_id"], model, prev)
        else:
            if model in MODELS:
                return await self.update_audits(model.__name__, data, record, prev)
        return await self.delete_unneeded_data(record)

    @run_in_thread_pool
    async def update_db_entries(self, stmt: Any, record: dict):
        print(f"Updating model with record: \n\t{record}")
        with create_db() as db:
            model = db.merge(stmt)
            for col in model.__table__.c:
                prev = getattr(model, col.key)
                if col.key != "id" and col.key in record and record[col.key]:
                    if not isinstance(prev, (float, int)):
                        if isinstance(record[col.key], type(prev)):
                            setattr(model, col.key, record[col.key])
                    else:
                        setattr(
                            model,
                            col.key,
                            (
                                record[col.key]
                                if not isinstance(record[col.key], str)
                                else prev + int(float(record[col.key]))
                            ),
                        )
                else:
                    setattr(
                        model,
                        col.key,
                        (
                            prev
                            if not col.key.startswith("upd")
                            else datetime.datetime.now()
                        ),
                    )
            db.commit()
            db.refresh(model)
            return await self.update_audits(
                model,
                record,
                await self.read_stmt_to_dict(model),
                await self.read_stmt_to_dict(stmt),
            )

    @run_in_thread_pool
    async def delete_unneeded_data(
        self, data: dict, flags: tuple = ("otp", "password")
    ):
        data = {k: data[k] for k in data.keys() if k not in flags}
        for k in data.keys():
            if k.endswith("id"):
                data[k] = await self.convert_id(data[k])
            elif isinstance(data[k], datetime.datetime):
                data[k] = data[k].isoformat()
        return data

    @run_in_thread_pool
    async def check_if_values_upd(
        self, data: list | dict, nxt: dict, model: Any, flag: str = None
    ):
        if data:
            data = [data] if not isinstance(data, list) else data
            for rec in data:
                for k in nxt.keys():
                    if k.endswith("_id"):
                        if (
                            k in rec
                            and rec[k] == nxt[k]
                            or k in find_fit_model.collect_cols(model)
                        ):
                            for x in rec.keys():
                                if not x.startswith(self.ts_flags) and not x.endswith(
                                    "id"
                                ):
                                    if x in nxt:
                                        if isinstance(
                                            rec[x], str
                                        ) and find_fit_model.check_if_a_compares_b(
                                            nxt[x], rec[x]
                                        ):
                                            if flag:
                                                for y in rec.keys():
                                                    if isinstance(rec[y], str):
                                                        for z in nxt.copy().keys():
                                                            if (
                                                                isinstance(
                                                                    nxt[z], type(rec[y])
                                                                )
                                                                and nxt[z] == rec[y]
                                                            ):
                                                                if not find_fit_model.check_if_a_compares_b(
                                                                    z, y
                                                                ):
                                                                    del nxt[z]
                                            return await self.read_stmt(
                                                model,
                                                rec["id" if not flag else flag],
                                                flag="upd",
                                            )
            from utils.rel import upd, relshp

            if upd.return_keys(data[0].keys()) == upd.return_keys(
                find_fit_model.collect_cols(model)
            ):
                for m in MODELS:
                    if m != model:
                        res = await self.read_stmt(m, data[0]["id"])
                        if res:
                            return await self.check_if_values_upd(
                                res,
                                nxt,
                                model,
                                relshp.check_if_model_contains_relations(m)[1],
                            )
        return None

    @run_in_thread_pool
    async def check_if_update_or_new_entry(
        self, data: dict, model: Any, out: str = None, flag: bool = False
    ):
        data = clean_data(data)
        for k in data.keys():
            if k in find_fit_model.collect_cols(model):
                if k != out and isinstance(data[k], str):
                    if flag or k.endswith("_id") != -1:
                        upd = await self.check_if_values_upd(
                            await self.read_stmt(model, data[k]), data, model
                        )
                        if upd:
                            return upd
        return (
            await self.check_if_update_or_new_entry(data, model, out, True)
            if not flag
            else None
        )

    @staticmethod
    @run_in_thread_pool
    async def delete_user(id: str, stmt: Any):
        from r_services.service import r_service

        with create_db() as db:
            await r_service.invalidate_cache(id)
            db.delete(stmt)
            db.commit()
            return {"message": "Success deleting all your data!!"}


read_stmt = ReadStatements()
from utils.find_fit import find_fit_model
