from typing import Any

from utils.find_fit import find_fit_model
from utils.stmt import read_stmt
from utils.extras import MODELS, clean_data


class FindRelationBtwData:
    def __init__(self):
        self.models = MODELS

    async def check_if_rel_is_needed(self, record: dict, mod: Any):
        record = clean_data(record)
        if mod.__name__.endswith("tory"):
            from utils.cog_pricing import est_price

            record = est_price.calculate_cog_from_r_price(record)
        exist = self.check_if_relshp_v_exist(mod, record)
        if exist:
            return await self.write_to_dependency(
                record,
                self.find_where_else_data_might_exist(mod),
                mod,
            )
        tn, key = self.check_if_model_contains_relations(mod)
        wrote = await self.find_belongs_to(tn, record)
        if not wrote:
            raise ValueError(f"Failed writing record to model: {tn}!!")
        record[key] = wrote["id"]
        upd = self.check_if_data_update(mod, record)
        if upd:
            if not isinstance(upd, dict):
                wrote.update(await read_stmt.update_db_entries(upd, record))
            else:
                wrote.update(upd)
        else:
            wrote.update(read_stmt.write_items_to_db(mod, record))
        return wrote

    @staticmethod
    def check_if_model_contains_relations(model: Any):
        for col in model.__table__.c:
            if col.foreign_keys:
                for fk in col.foreign_keys:
                    return (fk.column.table.name, col.key)
        return None

    def find_where_else_data_might_exist(self, mod: Any, result: set = set()):
        for m in self.models:
            if m != mod:
                if mod.__tablename__ == self.check_if_model_contains_relations(m)[0]:
                    result.add(m)
        return result

    async def write_to_dependency(
        self, record: dict, deps: set, mod: Any, infered: dict = None
    ):
        upd = self.check_if_data_update(mod, record)
        if upd:
            if not isinstance(upd, dict):
                upd = await read_stmt.update_db_entries(upd, record)
        else:
            upd = read_stmt.write_items_to_db(mod, record)
        if not deps:
            return upd
        print(f"Model name to flag out: {mod.__name__} with deps: {deps}")
        while deps:
            infer, record = find_fit_model.find_similarity_in_columns(record, mod)
            if infer["m"] == mod or infer["m"] not in deps:
                if not infered:
                    raise ValueError(
                        f"Error, infer model same as found model...{infer['m']} : {mod}"
                    )
                elif infered["m"] == infer["m"]:
                    break
            elif (
                not infered
                or infered["v"] < infer["v"]
                or len(infered["k"]) < len(infer["k"])
            ):
                infered = infer
            deps = deps.difference([infer["m"]])

        if not infered:
            raise ValueError("Failed to find infered from deps!!")
        record[self.check_if_model_contains_relations(infered["m"])[1]] = upd["id"]
        n_upd = self.check_if_data_update(infer["m"], record)
        if n_upd:
            if not isinstance(n_upd, dict):
                upd.update(await read_stmt.update_db_entries(n_upd, record))
            else:
                upd.update(n_upd)
        else:
            upd.update(read_stmt.write_items_to_db(infer["m"], record))
        return upd

    async def find_belongs_to(self, tn: str, record: dict, inf: Any = None):
        print(f"Finding parent model with table name: {tn}")
        if tn.endswith("ory"):
            from utils.cog_pricing import est_price

            record = est_price.calculate_cog_from_r_price(record)
        for model in self.models:
            if model.__tablename__ == tn:
                infer, record = find_fit_model.find_similarity_in_columns(record, inf)
                if infer["m"] != model:
                    print(f"Error, returned for infer to model: {infer['m']} : {model}")
                    return await self.find_belongs_to(tn, record, infer["m"])
                upd = self.check_if_data_update(model, record)
                if upd:
                    if not isinstance(upd, dict):
                        return await read_stmt.update_db_entries(upd, record)
                    return upd
                return read_stmt.write_items_to_db(model, record)
        return None

    @staticmethod
    def check_if_relshp_v_exist(model: Any, record: dict):
        for col in model.__table__.c:
            if col.key.endswith("_id") and col.key in record:
                return True
        return False

    def check_if_data_update(self, model: Any, record: dict):
        upd = read_stmt.check_if_update_or_new_entry(record, model)
        if not upd:
            return None
        n = read_stmt.read_stmt_to_dict(upd)
        if self.handle_if_equality_assumed(self.return_keys(n.keys()), n, record):
            return read_stmt.read_stmt_to_dict(upd)
        n = self.find_rel_upd_of_n(n, model, record)
        if n:
            if isinstance(n, dict):
                return read_stmt.read_stmt_to_dict(upd)
            res = self.compare_ns_to_act(read_stmt.read_stmt_to_dict(upd), n[0], record)
            if res:
                for r in res:
                    if r and not isinstance(r, str):
                        self.cache_flag_update(model.__tablename__, r)
        return upd

    def find_rel_upd_of_n(self, record: dict, model: Any, nxt: dict):
        for m in self.models:
            if m != model:
                for k in record.keys():
                    if k.endswith("id"):
                        data = read_stmt.read_stmt(m, record[k])
                        if data:
                            if isinstance(data, dict):
                                data = [data]
                            for d in data:
                                for x in d.keys():
                                    if isinstance(d[x], str) and d[x] in nxt.values():
                                        if record["updated"] and d["updated"]:
                                            from datetime import datetime

                                            mx = (
                                                datetime.now()
                                                - record["updated"]
                                                - d["updated"]
                                            )
                                            el = record["updated"] - d["updated"]
                                            if el.seconds <= mx.seconds / 2:
                                                if self.handle_if_equality_assumed(
                                                    self.return_keys(d.keys()),
                                                    d,
                                                    nxt,
                                                ):
                                                    return {
                                                        "error": "Update already made skip record!!"
                                                    }
                                        return (d, m)
        return None

    @staticmethod
    def check_linear_exist(act: int, nxt: int, key: tuple, p_act: int = 100):
        if not key:
            raise ValueError("Func collect_key failed to find actual key from values!")
        l = (nxt / act) * p_act
        if l not in range(p_act - 5, p_act + 5):
            return {key[0]: key[1]}
        return None

    @staticmethod
    def collect_actual_key_if_found(key: str, record: dict):
        for k in record.keys():
            if k != key:
                if isinstance(record[k], type(record[key])):
                    if record[key] == record[k]:
                        return (k, "-")
        return (key, "+")

    @staticmethod
    def cache_flag_update(key: str, data: dict):
        from r_services.service import r_service

        return r_service.cache_data(key, data, 60 * 5)

    def compare_ns_to_act(self, a: dict, b: dict, c: dict, res: list = []):
        if a != c or b != c:
            print("Checking for updates in data...")
            for k in c.keys():
                if not k.endswith(("id", "ed")):
                    if k in a:
                        res.append(self.compare_data(c, a, k))
                    elif k in b:
                        res.append(self.compare_data(c, b, k))
        return res

    def compare_data(self, a: dict, b: dict, k: str):
        if a[k] != b[k]:
            if not isinstance(a[k], (float, int)):
                return k
            elif isinstance(a[k], int):
                return self.check_linear_exist(
                    b[k], a[k], self.collect_actual_key_if_found(k, a)
                )
            elif not k.startswith("amo"):
                from utils.cog_pricing import est_price

                return {
                    "amount": {
                        "x": f"-{est_price.calculate_cog_from_r_price(b)['amount'] * b['stock']}",
                        "y": f"{est_price.calculate_cog_from_r_price(a)['amount'] * (b['stock'] + (a['stock'] - b['stock']))}",
                    }
                }
            elif not "phone" in a:
                return {k: "+"}
            elif a[k] > b[k]:
                return {k: "+"}
            return {k: "-"}
        return None

    @staticmethod
    def return_keys(data: set):
        return [x for x in data if not x.endswith(("id", "ed"))]

    @staticmethod
    def handle_if_equality_assumed(keys: list, n: dict, act: dict):
        for k in keys:
            if k in n and k in act:
                if n[k] != act[k]:
                    return False
        return True


relshp = FindRelationBtwData()
