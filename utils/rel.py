from sqlite3 import IntegrityError
from typing import Any

from utils.find_fit import find_fit_model
from utils.stmt import read_stmt
from utils.extras import MODELS, TS_FLAGS, clean_str
from utils.cog_pricing import est_price


class FindRelationBtwData:
    def __init__(self):
        self.models = MODELS
        self.user_rel_m = ("inventory", "expense", "operation")

    async def check_if_rel_is_needed(self, record: dict, mod: Any):
        if mod.__name__.endswith("tory") and not "amount" in record:
            record = est_price.calculate_cog_from_r_price(record)
        exist = await self.check_if_relshp_v_exist(mod, record)
        if exist:
            deps = self.find_else_r_might_exist_in_models(
                (mod, exist[0] if isinstance(exist, tuple) else None)
            )
            if deps:
                deps.extend([mod, exist[0] if isinstance(exist, tuple) else None])
            return await self.write_to_dependency(record, deps)
        tn, key = self.check_if_model_contains_relations(mod)
        wrote = await self.find_belongs_to(tn, record, mod)
        if not wrote or not "id" in wrote:
            raise ValueError(
                f"Failed writing record to model: {tn} with values:\n {wrote}!!"
            )
        record[key] = wrote["id"]
        wrote.update(await self.update_write_or_return(mod, record))
        return wrote

    @staticmethod
    def check_if_model_contains_relations(model: Any):
        for col in model.__table__.c:
            if col.foreign_keys:
                for fk in col.foreign_keys:
                    return (fk.column.table.name, col.key)
        return None

    def find_else_r_might_exist_in_models(
        self, models: tuple = None, result: list = None
    ):
        if models:
            for m in self.models:
                if m not in models:
                    for mod in models:
                        if (
                            mod
                            and mod.__tablename__
                            == self.check_if_model_contains_relations(m)[0]
                        ):
                            if not result:
                                result = [m]
                            elif m not in result:
                                result.append(m)
        return result

    async def write_to_dependency(self, record: dict, models: list, res: list = []):
        for m in models:
            models = [x for x in models if x != m]
            if m:
                rel = self.check_if_model_contains_relations(m)
                if res:
                    record[rel[1]] = res[-1]["id"]
                elif not rel[1] in record or m.__tablename__ != rel[0]:
                    print(f"Finding parent model for model: {m} with parent {rel[0]} ")
                    infer = await find_fit_model.find_similarity_in_columns(
                        record, (m,), rel[0]
                    )
                    while (
                        isinstance(infer, tuple)
                        and infer[0]["m"].__tablename__ != rel[0]
                    ):
                        infer = await find_fit_model.find_similarity_in_columns(
                            record,
                            (
                                infer["m"],
                                m,
                            ),
                            rel[0],
                        )
                    if isinstance(infer, tuple):
                        if infer[0]["m"] in models:
                            models.remove(infer[0]["m"])
                        res.append(
                            await self.update_write_or_return(infer[0]["m"], infer[1])
                        )
                        models.append(m)
                    else:
                        print(f"Error returned with value: \n\t {infer}")
                        record.update(infer)
                        res.append(record)
                else:
                    res.append(await self.update_write_or_return(m, record))
        return res

    async def find_belongs_to(self, tn: str, record: dict, mod: Any):
        if tn.endswith("tory"):
            record = est_price.calculate_cog_from_r_price(record)
        for model in self.models:
            if model.__tablename__ == tn:
                infer = await find_fit_model.find_similarity_in_columns(
                    record, (mod,), tn
                )
                if isinstance(infer, tuple):
                    while isinstance(infer, tuple) and infer[0]["m"] != model:
                        print(f"Recursing due inquality model: {infer['m']}: {model}")
                        infer = await find_fit_model.find_similarity_in_columns(
                            record,
                            (
                                infer["m"],
                                mod,
                            ),
                            tn,
                        )
                    return (
                        await self.update_write_or_return(model, infer[1])
                        if isinstance(infer, tuple)
                        else infer
                    )
                return infer
        return None

    async def check_if_relshp_v_exist(self, model: Any, record: dict):
        for k in record.copy().keys():
            if k.endswith("id"):
                for m in self.models:
                    if m != model and record[k] in [
                        id for id in await read_stmt.read_stmt(m, column="id")
                    ]:
                        record[self.check_if_model_contains_relations(model)[1]] = (
                            record[k]
                        )
                        del record[k]
                        return (m, record)
                from utils.find_fit import find_fit_model

                if (
                    k.endswith("id")
                    and k != "id"
                    and k in find_fit_model.collect_cols(model)
                ):
                    return record
        return None

    async def update_write_or_return(self, model: Any, record: dict):
        try:
            update = await upd.check_if_update(record, model, model.__tablename__)
            if update:
                if isinstance(update, tuple):
                    return await read_stmt.update_db_entries(update[0], update[1])
                return update
            return await read_stmt.write_items_to_db(model, record)
        except IntegrityError:
            return await self.check_if_rel_is_needed(record, model)


relshp = FindRelationBtwData()
import time


class FindUpdate:
    def __init__(self):
        self.models = MODELS
        self.ts_flags = TS_FLAGS
        self.user_flags = ("users", "admins")
        self.tn_flags = ("catalog", "product")

    def collect_foreign_keys(self, f_keys: dict = {}):
        for m in self.models:
            rel = relshp.check_if_model_contains_relations(m)
            if not rel[1] in self.f_keys:
                f_keys[rel[1]] = [rel[0]]
            elif rel[0] not in self.f_keys[rel[1]]:
                f_keys[rel[1]].append(rel[0])
        return f_keys

    def return_keys(self, keys: set):
        return {
            clean_str(k)
            for k in keys
            if not k.startswith(self.ts_flags) and not "id" in k
        }

    async def check_if_update(self, record: dict, model: Any, tn: str):
        exist = await read_stmt.check_if_update_or_new_entry(record, model)
        print(f"Exist with values: {exist}")
        if tn == "sales":
            time.sleep(5)
        if exist:
            prev = await read_stmt.read_stmt_to_dict(exist)
            if self.check_inequality(prev, record):
                inqs = await self.find_how_update_occurs_btw_prev_nxt(prev, record, tn)
                if inqs:
                    if not isinstance(inqs, str):
                        if not isinstance(inqs, tuple):
                            return inqs
                        inqs, record = inqs
                        for k in record.keys():
                            if k in inqs and not isinstance(record[k], str):
                                record[k] = inqs[k] + str(record[k])
                    return (exist, record)
            return prev
        return None

    @staticmethod
    def compare_ts(r: dict, p_rec: dict):
        def ts(micro: int = 1000):
            from datetime import timedelta, datetime

            return datetime.now() - timedelta(microseconds=micro)

        if r:
            if r["updated"] and p_rec["updated"]:
                if r["updated"] > p_rec["updated"]:
                    if r["updated"] > ts():
                        if p_rec["updated"] > ts():
                            return None
                elif p_rec["updated"] > ts():
                    return None
        elif p_rec["updated"] and p_rec["updated"] > ts() or p_rec["created"] > ts():
            return None
        return "update"

    def find_equality_of_keys(self, prev: dict, record: dict) -> str | tuple[str]:
        if prev.keys() != record.keys():
            if "id" in record and record["id"] == prev["id"]:
                if len(prev.keys()) > len(record.keys()):
                    return ("deduct", "child")
                return ("update", "parent")
            elif self.return_keys(prev.keys()) != self.return_keys(record.keys()):
                if len(self.return_keys(prev.keys())) != len(
                    self.return_keys(record.keys())
                ):
                    if len(self.return_keys(prev.keys())) > len(
                        self.return_keys(record.keys())
                    ):
                        return ("update", "child")
            return ("update", "parent")
        return ("replace", "child", "parent")

    async def find_how_update_occurs_btw_prev_nxt(self, prev: dict, nxt: dict, tn: str):
        form = self.find_equality_of_keys(prev, nxt)
        for m in self.models:
            if m.__tablename__ != tn:
                rel = relshp.check_if_model_contains_relations(m)
                from utils.find_fit import find_fit_model

                for f in form:
                    if (
                        f in ("child", "parent")
                        and rel[0] == tn
                        or rel[-1] in find_fit_model.collect_cols(m)
                    ):
                        inqs = await self.find_how_update_occurs_btw_rels(
                            nxt,
                            prev,
                            form,
                            tn,
                            await read_stmt.read_stmt_to_dict(
                                await read_stmt.check_if_update_or_new_entry(nxt, m)
                            ),
                        )
                        if inqs:
                            return inqs

    @staticmethod
    async def update_conflict_to_audit_logs(
        act: dict, prev: dict, tn: str, extra: dict = None, flag: str = None
    ):
        await read_stmt.update_audits(tn, act, prev, extra)
        return {"error": f"{flag} confilct occurred btw updates!!"}

    def check_if_miss(self, prev: dict, rec: dict, extra: dict, typ: str):
        if typ == "child":
            for e in extra.keys():
                if isinstance(extra[e], (float, int)):
                    if not e in prev:
                        if not e in rec:
                            rec[e] = extra[e]
            f_keys = self.collect_foreign_keys({})
            if f_keys:
                for k in f_keys.keys():
                    if k in extra:
                        if "inventory" in f_keys[k] and not prev["total"]:
                            from utils.cog_pricing import est_price

                            rec = est_price.calculate_cog_from_r_price(rec)
        print(f"Missing data found and added with values: \n\t{rec}")
        return rec

    async def find_how_update_occurs_btw_rels(
        self, record: dict, prev: dict, form: tuple, tn, extra: dict = None
    ):
        if self.check_inequality(prev, record, extra):
            if self.compare_ts(extra, prev):
                inqs = {}
                for k in prev.keys():
                    if isinstance(prev[k], (float, int)) and k in record:
                        l = self.check_linear_update(prev[k], record[k])
                        if l:
                            if not isinstance(l, str):
                                x: Any = None
                                if extra:
                                    for f in form:
                                        record = self.check_if_miss(
                                            prev, record, extra, f
                                        )
                                    for e in extra.keys():
                                        if (
                                            isinstance(extra[e], (float, int))
                                            and e in record
                                        ):
                                            x = self.check_linear_update(
                                                extra[e], record[e], form[-1]
                                            )
                                            if x:
                                                if isinstance(x, str):
                                                    if x != "replace":
                                                        return await self.update_conflict_to_audit_logs(
                                                            record,
                                                            prev,
                                                            tn,
                                                            extra,
                                                            "rel-numeric",
                                                        )
                                                    else:
                                                        x = (x,)
                                inqs[k] = self.compare_form_with_linear(
                                    l + x if x else l, form
                                )
                            else:
                                if l != "replace":
                                    return await self.update_conflict_to_audit_logs(
                                        record, prev, tn, extra, "numeric"
                                    )
                                elif l in form:
                                    return l
                return (inqs, record) if inqs else None
            return await self.update_conflict_to_audit_logs(
                record, prev, tn, extra, "date"
            )
        return None

    @staticmethod
    def compare_form_with_linear(l: tuple, form: tuple):
        for x in l:
            if x and x in form:
                if x != "update":
                    return "-"
                return "+"
        raise ValueError(
            f"Failed to find update value from compares: \n {l} and {form}"
        )

    def check_inequality(self, rec: dict, nxt: dict, c_rec: dict = None):
        for k in nxt.keys():
            if k in rec and isinstance(nxt[k], type(rec[k])) and rec[k] != nxt[k]:
                if c_rec:
                    for x in nxt.keys():
                        if x in c_rec and isinstance(nxt[x], type(c_rec[x])):
                            if c_rec[x] != nxt[x]:
                                return True
                            elif isinstance(c_rec[x], (float, int)):
                                return False
                return True
        return False

    @staticmethod
    def check_linear_update(
        act: int | float, inc: int | float, f: str = "actual", l: float = 100
    ):
        if act != inc:
            if inc:
                if act:
                    move = inc / act * l
                    if move > l:
                        if f == "actual":
                            if move < l + 10:
                                return "replace"
                        return ("replace", "update")
                    elif f != "actual" and f == "child":
                        return ("replace", "deduct")
                return ("replace", "update")
            return ("replace", "deduct") if act - l == inc else "conflict"
        return None

    async def find_user_id(self, record: dict, exclude: tuple = tuple()):
        f_keys = self.collect_foreign_keys()
        for k in f_keys.keys():
            if k in record:
                for m in self.models:
                    if m.__tablename__ in f_keys[k][0]:
                        records = await read_stmt.read_stmt(m, record[k])
                        if records:
                            if isinstance(records, dict):
                                records = [records]
                            elif "user_id" in records[0]:
                                return records[0]["user_id"]
                            return await self.find_user_id(records[0], exclude + (m,))
        return None


upd = FindUpdate()
