from sqlite3 import IntegrityError
from typing import Any

from utils.find_fit import find_fit_model
from utils.stmt import read_stmt
from utils.extras import MODELS, TS_FLAGS
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
            print("Depends on: \n", deps)
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

    async def write_to_dependency(
        self,
        record: dict,
        models: list,
        res: list = [],
    ):
        for m in models:
            models = [x for x in models if x != m]
            if m:
                rel = self.check_if_model_contains_relations(m)
                if res:
                    record[rel[1]] = res[-1]["id"]
                elif not rel[1] in record:
                    infer, record = await find_fit_model.find_similarity_in_columns(
                        record, (m,)
                    )
                    while infer["m"].__tablename__ != rel[0]:
                        infer, record = await find_fit_model.find_similarity_in_columns(
                            record,
                            (
                                infer["m"],
                                m,
                            ),
                            rel[0],
                        )
                    if infer["m"] in models:
                        models.remove(infer["m"])
                    print(f"Model found from infer: {infer['m']} parent of {m}:")
                    res.append(await self.update_write_or_return(infer["m"], record))
                    models.append(m)
                else:
                    res.append(await self.update_write_or_return(m, record))
        return res

    async def find_belongs_to(self, tn: str, record: dict, mod: Any):
        print("Table found with name: ", tn)
        if tn.endswith("ory"):
            record = est_price.calculate_cog_from_r_price(record)
        for model in self.models:
            if model.__tablename__ == tn:
                infer, record = await find_fit_model.find_similarity_in_columns(
                    record, (mod,), tn
                )
                while infer["m"] != model:
                    print(f"Recursing due inquality model: {infer['m']}: {model}")
                    infer, record = await find_fit_model.find_similarity_in_columns(
                        record,
                        (
                            infer["m"],
                            mod,
                        ),
                        tn,
                    )
                return await self.update_write_or_return(model, record)
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
                if (
                    k.endswith("id")
                    and k != "id"
                    and k in [c.key for c in model.__table__.c]
                ):
                    return record
        return None

    async def update_write_or_return(self, model: Any, record: dict):
        try:
            update = await upd.check_if_update(record, model, model.__tablename__)
            if update and isinstance(update, tuple):
                return await read_stmt.update_db_entries(update[0], update[1])
            return (
                await read_stmt.write_items_to_db(model, record)
                if not update
                else update
            )
        except IntegrityError:
            return await self.check_if_rel_is_needed(record, model)


relshp = FindRelationBtwData()


class FindUpdate:
    def __init__(self):
        self.models = MODELS
        self.ts_flags = TS_FLAGS
        self.user_flags = ("users", "admins")
        self.tn_flags = ("catalog", "product")
        self.f_keys: dict = None

    def collect_foreign_keys(
        self,
    ):
        for m in self.models:
            rel = relshp.check_if_model_contains_relations(m)
            if rel:
                if not self.f_keys:
                    self.f_keys = {rel[1]: [rel[0]]}
                elif not rel[1] in self.f_keys:
                    self.f_keys[rel[1]] = [rel[0]]
                elif rel[0] not in self.f_keys[rel[1]]:
                    self.f_keys[rel[1]].append(rel[0])
        return None

    def return_keys(self, keys: set):
        return {
            k for k in keys if not k.endswith("id") and not k.startswith(self.ts_flags)
        }

    async def check_if_update(self, record: dict, model: Any, tn: str):
        print(f"Beginning update check on {tn}....")
        exist = await read_stmt.check_if_update_or_new_entry(record, model)
        if exist:
            prev = await read_stmt.read_stmt_to_dict(exist)
            if self.check_inequality(prev, record):
                inqs = await self.find_how_update_occurs_btw_prev_nxt(prev, record, tn)
                if inqs:
                    print("Inquired updates: \n", inqs)
                    if not isinstance(inqs, str):
                        for k in record.keys():
                            if k in inqs and not isinstance(record[k], str):
                                record[k] = inqs[k] + str(record[k])
                        print(f"Updating model: {tn} with values: \n {record}")
                    return (exist, record)
            return prev
        return None

    @staticmethod
    def compare_ts(r: dict, p_rec: dict):
        if (
            r[("updated" if r["updated"] else "created")]
            > p_rec[("updated" if p_rec["updated"] else "created")]
        ):
            return True
        return False

    def find_equality_of_keys(self, prev: dict, record: dict) -> str | tuple[str]:
        if prev.keys() != record.keys():
            if "id" in record and record["id"] == prev["id"]:
                if len(prev.keys) > len(record.keys()):
                    return ("deduct", "child")
                return ("update", "parent")
            elif self.return_keys(prev.keys()) != self.return_keys(record.keys()):
                if len(prev.keys) > len(record.keys()):
                    return ("update", "child")
            return ("update", "parent")
        return "replace"

    async def find_how_update_occurs_btw_prev_nxt(self, prev: dict, nxt: dict, tn: str):
        print("finding how update occurs based on previous entry!!")
        form = self.find_equality_of_keys(prev, nxt)
        if not isinstance(form, str):
            upd: Any = None
            for m in self.models:
                if form[-1] != "child":
                    if relshp.check_if_model_contains_relations(m)[1] in m.__table__.c:
                        upd = await read_stmt.check_if_update_or_new_entry(m, nxt)
                elif tn == relshp.check_if_model_contains_relations(m)[0]:
                    upd = await read_stmt.check_if_update_or_new_entry(m, nxt)
                elif upd:
                    return await self.find_how_update_occurs_btw_prev_nxt_if_extra(
                        nxt, prev, form, await read_stmt.read_stmt(upd)
                    )
            return await self.find_how_update_occurs_btw_prev_nxt_if_extra(
                nxt, prev, form
            )
        return form

    async def find_how_update_occurs_btw_prev_nxt_if_extra(
        self, record: dict, prev: dict, form: tuple, extra: dict = None
    ):
        res: dict = {}
        print("Checking update in 3->l rel...")
        for k in prev.keys():
            if k in record and isinstance(record[k], type(prev[k])):
                if isinstance(prev[k], (float, int)):
                    l = self.check_linear_update(prev[k], record[k])
                    if extra:
                        if k in extra and isinstance(record[k], type(extra[k])):
                            x = self.check_linear_update(extra[k], record[k])
                            if x != l:
                                if isinstance(x, type(l)):
                                    if not isinstance(x, str):
                                        l = l + x
                                    else:
                                        l = (l, x)
                                else:
                                    if isinstance(l, tuple) and isinstance(x, str):
                                        l = l + (x,)
                                    elif isinstance(x, tuple) and isinstance(l, str):
                                        l = x + (l,)
                    res[k] = self.compare_form_with_linear(l, form)
        return res

    @staticmethod
    def compare_form_with_linear(l: tuple, form: tuple):
        for x in l:
            if x in form:
                if x != "update":
                    return "-"
                return "+"
        raise ValueError(
            f"Failed to find update value from compares: \n {l} and \n {form}"
        )

    def check_inequality(self, p_rec: dict, nxt: dict, c_rec: dict = None):
        for k in nxt.keys():
            if not k.endswith("id") and not k.startswith(self.ts_flags):
                if k in p_rec:
                    if isinstance(nxt[k], type(p_rec)) and p_rec[k] != nxt[k]:
                        return True
                elif c_rec and k in c_rec:
                    if isinstance(nxt[k], type(c_rec[k])) and c_rec[k] != nxt[k]:
                        return True
        return False

    @staticmethod
    def check_linear_update(
        act: int | float, inc: int | float, l: int = 100
    ) -> str | tuple[str]:
        if inc:
            if act:
                move = inc / act * l
                if move > l:
                    return ("replace", "update")
                return ("replace", "deduct")
            return "update"
        return "conflict"

    async def find_user_id(self, record: dict):
        if not self.f_keys:
            self.collect_foreign_keys()
        for k in self.f_keys.keys():
            if k in record:
                for m in self.models:
                    if m.__tablename__ == self.f_keys[k][0]:
                        records = await read_stmt.read_stmt(m, record[k])
                        if records:
                            if isinstance(records, dict):
                                records = [records]
                            elif "user_id" in records[0]:
                                return records[0]["user_id"]
                            return await self.find_user_id(records[0])
        return None


upd = FindUpdate()
