import datetime
import re

from typing import Any
from sqlalchemy import inspect
from sqlalchemy import select
from sqlalchemy.sql import sqltypes

from database.config import create_db
from database.models import GUID


class ReadStatements:
    def __init__(self):
        self.flags = {"inventory", "creditors"}
        self.f_cols = {
            "name",
            "product",
        }
        self.name_exp = re.compile(r'[a-z/\-/d/a-z]')

    def read_stmt(self, model: Any, query: str = None, c: Any = None):
        if not model:
            return None
        stmts: Any = None
        with create_db() as db:
            if query is None:
                if c is None:
                    stmts = db.scalars(select(model)).all()
                stmts = db.scalars(select(model).column(c)).all()
            else:
                for col in model.__table__.c:
                    stmts = db.scalars(select(model).where(col == query)).all()
                    if not len(stmts):
                        continue
                    break
            if not stmts:
                return None
            result = []
            for stmt in stmts:
                if not stmt:
                    continue
                data = self.read_stmt_to_dict(stmt)
                if len(stmts) > 1:
                    if data not in result:
                        result.append(data)
                        continue
                    continue
                return data
            return result

    @staticmethod
    def read_stmt_to_dict(stmt: Any):
        try:
            return {
                c.key: getattr(stmt, c.key)
                for c in inspect(stmt, raiseerr=ValueError).mapper.column_attrs
            }
        except ValueError:
            result = {}
            for col in stmt.__table__.c:
                if not col.key in result:
                    result[col.key] = getattr(stmt, col.key)
            return result

    @staticmethod
    def convert_id(id: sqltypes.UUID):
        return GUID().process_result_value(id)

    def write_items_to_db(self, model: Any, data: dict):
        m_name = model.__name__.lower()
        for x, y in data.items():
            if m_name.find("inv") != -1:
                if x == 'category':
                    upd = self.read_model_for_update_convinience(model, data["category"])
                    if upd:
                        if data['user_id'] == upd.user_id:
                            return self.update_db_entries(upd, data)
                        break
                    break
                continue
            elif m_name.find("log", 3) != -1:
                if x != "i_id":
                    continue
                upd = self.read_model_for_update_convinience(model, y)
                if upd:
                    upd = self.read_model_for_update_convinience(model, data['brand'])
                    if upd:
                        return self.update_db_entries(upd, data)
                    break
                break
            elif m_name == "sales":
                if x != "p_id":
                    continue
                upd = self.read_model_for_update_convinience(model, y)
                if upd:
                    return self.update_db_entries(upd, data)
                break
            elif isinstance(y, str):
                upd = self.read_model_for_update_convinience(model, y)
                if upd:
                    return self.update_db_entries(upd, data)
                continue
        """upd = self.check_if_update_or_new_entry(data, model)
        if upd:
            if isinstance(upd, dict):
                return upd
            return self.update_db_entries(upd, data)"""
        

        mod = model()
        with create_db() as db:
            for col in mod.__table__.c:
                if col.key == "id":
                    continue
                elif col.key in data:
                    setattr(mod, col.key, data[col.key])
                    continue
                continue

            db.add(mod)
            db.commit()

            return self.delete_unneeded_data(self.read_stmt_to_dict(mod))

    def update_db_entries(self, stmt: Any, record: dict):
        with create_db() as db:
            model = db.merge(stmt)
            for col in model.__table__.c:
                if col.key != "id":
                    if col.key != "updated":
                        if col.key in record:
                            setattr(model, col.key, record[col.key])
                            continue
                        setattr(model, col.key, getattr(model, col.key))
                        continue
                    setattr(model, col.key, datetime.datetime.now())
                    continue
                setattr(model, col.key, getattr(model, col.key))
                continue

            db.commit()
            db.refresh(model)

            return self.delete_unneeded_data(self.read_stmt_to_dict(model))

    @staticmethod
    def delete_unneeded_data(data: dict):
        res = {}
        for k, v in data.items():
            if v is None:
                continue
            elif not isinstance(v, (str, int, float)):
                if isinstance(v, datetime.datetime):
                    res[k] = v.isoformat()
                    continue
                continue
            res[k] = v
            continue

        if "otp" in res:
            del res["otp"]
        elif "password" in res:
            del res["password"]
        return res

    @staticmethod
    def read_model_for_update_convinience(model: Any, query: str):
        with create_db() as db:
            for col in model.__table__.c:
                data = db.scalars(select(model).where(col == query)).first()
                if data:
                    return data
                continue
            return None

    def check_if_values_upd(self, prev: dict, nxt: dict):
        same = {'s': 0, 'n': 0}
        unsame = {'s': 0, 'n': 0}

        for k, v in prev.items():
            if k in nxt:
                if not isinstance(v, (float, int)):
                    if not isinstance(nxt[k], str):
                        continue
                    elif v != nxt[k]:
                        unsame["s"] += 1
                        continue
                    same["s"] += 1
                    continue
                elif v != nxt[k]:
                    unsame["n"] += 1
                    continue
                same["n"] += 1
                continue
            continue
        #same string + unsame numeric = update
        #unsame string + same numeric = update
        #
        if same["s"] > 0 and unsame["n"] > 0:
            return True
        elif unsame["s"] > 0 and same["n"] > 0:
            return True
        elif same["s"] > 0 and unsame['s'] > 0:
            return True
        return False
    
    def check_if_update_or_new_entry(self, data: dict, model: Any):
        m_name = model.__name__.lower()

        if m_name.find('tory', 3) != -1:
            if 'user_id' in data:
                upd = self.read_model_for_update_convinience(model, data['user_id'])
                if upd:
                    is_upd = self.check_if_values_upd(self.read_stmt_to_dict(upd), data)
                    if is_upd:
                        return upd
                    return None
                return None
            return {'error': 'Missing user_id  from record!!'}
        elif m_name.find('log', 4) != -1:
            if 'i_id' in data:
                upd = self.read_model_for_update_convinience(model, data['i_id'])
                if upd:
                    is_upd = self.check_if_values_upd(self.read_stmt_to_dict(upd), data)
                    if is_upd:
                        return upd
                    return None
                return None
            return {'error': f'Missing rel i_id in data!!'}
        elif m_name.find('ales', 1) != -1:
            if 'p_id' in data:
                upd = self.read_model_for_update_convinience(model, data['p_id'])
                if upd:
                    is_upd = self.check_if_values_upd(self.read_stmt_to_dict(upd), data)
                    if is_upd:
                        return upd
                    return None
                return None
            return {'error': 'Missing rel p_id in data'}
        for k, v in data.items():
            print('Key checking through update: ', k)
            if not isinstance(v, str):
                continue
            upd = self.read_model_for_update_convinience(model, v)
            if upd:
                is_upd = self.check_if_values_upd(self.read_stmt_to_dict(upd), data)
                if is_upd:
                    return upd
                continue
            continue
        return None





read_stmt = ReadStatements()
