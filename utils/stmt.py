import datetime

from typing import Any
from database.config import create_db
from utils.extras import run_in_thread_pool, MODELS


class ReadStatements:
    def __init__(self):
        pass

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
                if col.key in data and col.key != "id":
                    try:
                        if isinstance(data[col.key], col.type.python_type):
                            setattr(mod, col.key, data[col.key])
                    except Exception:
                        setattr(mod, col.key, data[col.key])
            db.add(mod)
            db.commit()
            return await self.update_audits(
                model, data, await self.read_stmt_to_dict(mod)
            )

    async def update_audits(self, model, data, record: dict, prev: dict = None):
        if model in MODELS:
            from services.pos.audits import audit_log

            if "user_id" in data:
                await audit_log.add_audit_log(
                    record, data["user_id"], model.__name__, prev
                )
            else:
                from utils.rel import upd

                user_id = await upd.find_user_id(record)
                if not user_id:
                    raise ValueError("Failed to find user id!!")
                await audit_log.add_audit_log(
                    record, data["user_id"], model.__name__, prev
                )
        return await self.delete_unneeded_data(record)

    @run_in_thread_pool
    async def update_db_entries(self, stmt: Any, record: dict):
        with create_db() as db:
            model = db.merge(stmt)
            for col in model.__table__.c:
                prev = getattr(model, col.key)
                if col.key in record and col.key != "id":
                    if not isinstance(prev, (float, int)):
                        if not isinstance(prev, str):
                            setattr(model, col.key, record[col.key])
                        else:
                            setattr(
                                model,
                                col.key,
                                record[col.key] if record[col.key] else prev,
                            )
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
                elif col.key.startswith("upd"):
                    setattr(model, col.key, datetime.datetime.now())
                else:
                    setattr(model, col.key, prev)
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
    async def check_if_values_upd(self, data: list | dict, nxt: dict, model: Any):
        if data:
            if not isinstance(data, list):
                data = [data]
            for rec in data:
                for k in rec.keys():
                    if not k.endswith(("id", "ed")):
                        if isinstance(rec[k], str) and k in nxt and nxt[k] == rec[k]:
                            return await self.read_stmt(model, rec["id"], flag="upd")
        return None

    @run_in_thread_pool
    async def check_if_update_or_new_entry(
        self, data: dict, model: Any, flag: bool = False
    ):
        for k in data.keys():
            if flag or k.find("id") != -1 and isinstance(data[k], str):
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
