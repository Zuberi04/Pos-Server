import datetime

from typing import Any
from database.config import create_db


class ReadStatements:
    def __init__(self):
        pass

    def read_stmt(self, model: Any, query: str = None, flag: str = None):
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
                        return db.scalars(select(model).where(col == query)).first()
                    stmts = db.scalars(select(model).where(col == query)).all()
                    if stmts:
                        break
            if not stmts:
                return None
            result = []
            for stmt in stmts:
                result.append(self.read_stmt_to_dict(stmt))
            return result if len(result) > 1 else result[0]

    @staticmethod
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
    def convert_id(id: Any):
        from database.models import GUID

        return GUID().process_result_value(id)

    def write_items_to_db(self, model: Any, data: dict):
        mod = model()
        with create_db() as db:
            for col in mod.__table__.c:
                if col.key != "id":
                    if col.key in data:
                        setattr(mod, col.key, data[col.key])
            db.add(mod)
            db.commit()

            return self.delete_unneeded_data(self.read_stmt_to_dict(mod))

    async def update_db_entries(self, stmt: Any, record: dict):
        with create_db() as db:
            model = db.merge(stmt)
            for col in model.__table__.c:
                prev = getattr(model, col.key)
                if col.key != "id":
                    if col.key in record:
                        if not isinstance(prev, (float, int)):
                            if not isinstance(prev, str):
                                if col.key.startswith("upd"):
                                    setattr(model, col.key, datetime.datetime.now())
                                else:
                                    setattr(model, col.key, prev)
                            else:
                                setattr(model, col.key, record[col.key])
                        else:
                            from r_services.service import r_service
                            from utils.extras import decode_json_objects

                            f = await r_service.collect_cache(
                                model.__tablename__, col.key
                            )
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
                else:
                    setattr(model, col.key, prev)

            db.commit()
            db.refresh(model)

            return self.delete_unneeded_data(self.read_stmt_to_dict(model))

    @staticmethod
    def delete_unneeded_data(data: dict, flag: set = {"otp", "password"}):
        for k in data.copy().keys():
            if k not in flag:
                if isinstance(data[k], datetime.datetime):
                    data[k] = data[k].isoformat()
            else:
                data = {x: data[x] for x in data.keys() if x != k}
        return data

    def check_if_values_upd(self, data: list | dict, nxt: dict, model: Any):
        if data:
            if not isinstance(data, list):
                data = [data]
            for rec in data:
                for k in rec.keys():
                    if not k.endswith(("id", "ed")):
                        if isinstance(rec[k], str):
                            if k in nxt and nxt[k] == rec[k]:
                                return self.read_stmt(model, rec["id"], "upd")
        return None

    def check_if_update_or_new_entry(self, data: dict, model: Any, flag: bool = False):
        for k in data.keys():
            if not flag:
                if k.find("id") == -1:
                    continue
                elif k in [c.key for c in model.__table__.c]:
                    upd = self.check_if_values_upd(
                        self.read_stmt(model, data[k]), data, model
                    )
                    if upd:
                        return upd
        if flag:
            return None
        return self.check_if_update_or_new_entry(data, model, True)


read_stmt = ReadStatements()
