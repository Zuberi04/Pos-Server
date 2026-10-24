from calendar import c
import datetime

from typing import Any
from database.config import create_db
from utils.extras import run_in_thread_pool


class ReadStatements:
    def __init__(self):
        pass

    @run_in_thread_pool
    async def read_stmt(self, model: Any, query: Any = None, flag: str = None):
        from sqlalchemy import select

        if not model:
            raise ValueError("Error, called without model passed to read!!")
        stmts: Any = None
        with create_db() as db:
            if query is None and flag is None:
                stmts = db.scalars(select(model)).all()
            else:
                for col in model.__table__.c:
                    if flag:
                        return db.scalars(
                            select(model).where(
                                col.type.python_type == type(query) and col == query
                                if col.key.find("id") == -1
                                else (
                                    col == query
                                    if isinstance(query, str)
                                    else col == await self.convert_id(query)
                                )
                            )
                        ).first()
                    stmts = db.scalars(
                        select(model).where(
                            col.type.python_type == type(query) and col == query
                            if col.key.find("id") == -1
                            else (
                                col == query
                                if isinstance(query, str)
                                else col == await self.convert_id(query)
                            )
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
        from sqlalchemy import inspect

        try:
            return {
                c.key: getattr(stmt, c.key)
                for c in inspect(stmt, raiseerr=ValueError).mapper.column_attrs
            }
        except ValueError:
            from utils.extras import clean_str

            return {
                clean_str(col.key): getattr(stmt, col.key, None)
                for col in stmt.__table__.c
            }

    @staticmethod
    @run_in_thread_pool
    def convert_id(id: Any):
        from database.models import GUID

        return GUID().process_result_value(id)

    @run_in_thread_pool
    async def write_items_to_db(self, model: Any, data: dict):
        mod = model()
        with create_db() as db:
            for col in mod.__table__.c:
                if col.key != "id":
                    if col.key in data:
                        setattr(mod, col.key, data[col.key])
            db.add(mod)
            db.commit()

            return await self.delete_unneeded_data(await self.read_stmt_to_dict(mod))

    @run_in_thread_pool
    async def update_db_entries(self, stmt: Any, record: dict):
        with create_db() as db:
            model = db.merge(stmt)
            for col in model.__table__.c:
                prev = getattr(model, col.key)
                if col.key in record:
                    if not isinstance(prev, (float, int)):
                        if not isinstance(prev, str):
                            setattr(model, col.key, record[col.key])
                        else:
                            if col.key.find("id") != -1:
                                if record[col.key].count("-") != 4:
                                    record[col.key] = prev
                            setattr(
                                model,
                                col.key,
                                record[col.key] if record[col.key] else prev,
                            )
                    else:
                        from r_services.service import r_service
                        from utils.extras import decode_json_objects

                        f = await r_service.collect_cache(model.__tablename__, col.key)
                        if f:
                            f = decode_json_objects(f)
                            if isinstance(f, dict):
                                setattr(
                                    model,
                                    col.key,
                                    prev + float(f["x"]) + float(f["y"]),
                                )
                            else:
                                setattr(
                                    model,
                                    col.key,
                                    prev + float(f + f"{record[col.key]}"),
                                )
                        else:
                            setattr(model, col.key, record[col.key])
                elif col.key.startswith("upd"):
                    setattr(model, col.key, datetime.datetime.now())
                elif prev:
                    setattr(model, col.key, prev)
            db.commit()
            db.refresh(model)

            return await self.delete_unneeded_data(await self.read_stmt_to_dict(model))

    @run_in_thread_pool
    async def delete_unneeded_data(self, data: dict, flag: set = {"otp", "password"}):
        for k in data.copy().keys():
            if k not in flag:
                if k.endswith("id"):
                    data[k] = await self.convert_id(data[k])
                elif isinstance(data[k], datetime.datetime):
                    data[k] = data[k].isoformat()
            else:
                data = {x: data[x] for x in data.keys() if x != k}
        return data

    @run_in_thread_pool
    async def check_if_values_upd(self, data: list | dict, nxt: dict, model: Any):
        if data:
            if not isinstance(data, list):
                data = [data]
            for rec in data:
                for k in rec.keys():
                    if not k.endswith(("id", "ed")):
                        if isinstance(rec[k], str):
                            if k in nxt and nxt[k] == rec[k]:
                                return await self.read_stmt(model, rec["id"], "upd")
        return None

    @run_in_thread_pool
    async def check_if_update_or_new_entry(
        self, data: dict, model: Any, flag: bool = False
    ):
        cols = [c.key for c in model.__table__.c]
        for k in data.keys():
            if not flag and k.find("id") == -1:
                continue
            elif k in cols:
                upd = await self.check_if_values_upd(
                    await self.read_stmt(model, data[k]), data, model
                )
                if upd:
                    return upd
        return (
            await self.check_if_update_or_new_entry(data, model, True)
            if not flag
            else None
        )


read_stmt = ReadStatements()
