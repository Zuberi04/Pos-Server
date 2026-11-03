from typing import Any

from utils.find_fit import find_fit_model
from utils.stmt import read_stmt
from utils.extras import MODELS
from utils.cog_pricing import est_price


class FindRelationBtwData:
    def __init__(self):
        self.models = MODELS

    async def check_if_rel_is_needed(self, record: dict, mod: Any, sleep: Any):
        if mod.__name__.endswith("tory") and not "amount" in record:
            record = est_price.calculate_cog_from_r_price(record)
        exist = await self.check_if_relshp_v_exist(mod, record)
        if exist or mod.__name__.endswith(("ry", "se")):
            return self.write_to_dependency(
                record,
                self.find_where_else_data_might_exist(
                    (mod, exist[0] if exist else exist)
                ),
                [mod, exist[0] if exist else exist],
            )
        tn, key = self.check_if_model_contains_relations(mod)
        wrote = await self.find_belongs_to(tn, record)
        if not wrote or not "id" in wrote:
            raise ValueError(
                f"Failed writing record to model: {tn} with values:\n {wrote}!!"
            )
        record[key] = wrote["id"]
        update = await upd.check_if_update(record, mod, mod.__tablename__)
        if update:
            if isinstance(upd, tuple):
                wrote.update(await read_stmt.update_db_entries(update[0], update[1]))
            else:
                wrote.update(update)
        else:
            wrote.update(await read_stmt.write_items_to_db(mod, record))
        return wrote

    @staticmethod
    def check_if_model_contains_relations(model: Any):
        for col in model.__table__.c:
            if col.foreign_keys:
                for fk in col.foreign_keys:
                    return (fk.column.table.name, col.key)
        return None

    def find_where_else_data_might_exist(
        self, models: tuple = None, result: set = set()
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
                            result.add(m)
        return result if len(result) else None

    async def write_to_dependency(
        self,
        record: dict,
        deps: set,
        models: list,
        infered: dict = None,
        r: bool = False,
        res: list = [],
    ):
        for m in models:
            if m:
                if res:
                    record[self.check_if_model_contains_relations(m)[1]] = res[-1]["id"]
                update = await upd.check_if_update(record, m, m.__tablename__)
                if update:
                    if isinstance(update, tuple):
                        res.append(
                            await read_stmt.update_db_entries(update[0], update[1])
                        )
                    else:
                        res.append(update)
                else:
                    if not models.index(m) and not r:
                        models.sort(reverse=True)
                        return await self.write_to_dependency(
                            record, deps, models, r=True
                        )
                    res.append(await read_stmt.write_items_to_db(m, record))
                r: int = 5
                while deps and r:
                    infer, record = find_fit_model.find_similarity_in_columns(record, m)
                    if infer["m"] in deps:
                        if infer["m"] not in models:
                            if infered:
                                if infered["m"] == infer["m"]:
                                    break
                                elif infered["v"] < infer["v"] and len(
                                    infered["k"]
                                ) < len(infer["k"]):
                                    infered = infer
                            else:
                                infered = infer
                        deps = deps.difference([infer["m"]])
                    r -= 1
                if infered:
                    record[self.check_if_model_contains_relations(infered["m"])[1]] = (
                        res[-1]["id"]
                    )
                    update = await upd.check_if_update(
                        record, infered["m"], infered["m"].__tablename__
                    )
                    if update:
                        if isinstance(update, tuple):
                            res.append(
                                await read_stmt.update_db_entries(update[0], update[1])
                            )
                        else:
                            res.append(update)
                    else:
                        res.append(
                            await read_stmt.write_items_to_db(infered["m"], record)
                        )
                elif m in models:
                    models.remove(m)
        return res

    async def find_belongs_to(self, tn: str, record: dict, inf: Any = None):
        print("Table found with name: ", tn)
        if tn.endswith("ory"):
            record = est_price.calculate_cog_from_r_price(record)
        for model in self.models:
            if model.__tablename__ == tn:
                infer, record = await find_fit_model.find_similarity_in_columns(
                    record, inf
                )
                if infer["m"] != model:
                    print(f"Recursing due inquality model: {infer['m']}: {model}")
                    return await self.find_belongs_to(tn, record, infer["m"])
                update = await upd.check_if_update(record, model, tn)
                if update:
                    if isinstance(update, tuple):
                        return await read_stmt.update_db_entries(update[0], update[1])
                    return update
                return await read_stmt.write_items_to_db(model, record)
        return None

    async def check_if_relshp_v_exist(self, model: Any, record: dict):
        rel = self.check_if_model_contains_relations(model)
        for m in self.models:
            if m.__tablename__ == rel[0]:
                ids = [id for id in await read_stmt.read_stmt(m, column="id")]
                print("IDS found with value: \n", ids)
                if ids:
                    for k in record.copy().keys():
                        if k.endswith("id") and record[k] in ids:
                            record[rel[1]] = record[k]
                            del record[k]
                            return (m, record)
        return None


relshp = FindRelationBtwData()
from time import sleep


class FindUpdate:
    def __init__(self):
        self.models = MODELS
        self.ts_flags = ("update", "create")
        self.user_flags = ("users", "admins")
        self.tn_flags = ("catalog", "product")
        self.f_keys: dict = None
        self.collect_foreign_keys()

    def collect_foreign_keys(self):
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

    async def find_update_values(
        self,
        record: dict,
        prev: dict,
        tn: str,
        inqs: dict[str, str] = None,
    ):
        print(
            f"Checking update for {tn} with prev record: \n {prev}\n And to update record: \n{record}"
        )
        inqs = {}
        for k in record.keys():
            if k != "id" and not k.startswith(self.ts_flags):
                if k in prev and prev[k] != record[k] and not k in inqs:
                    if isinstance(prev[k], (float, int)):
                        linear = self.check_linear_update(prev[k], record[k])
                        print("Linear occured with values: ", linear)
                        if not isinstance(linear, str):
                            occur = await self.find_how_update_occurs(prev, tn, record)
                            if (
                                not tn.startswith(self.tn_flags)
                                or k.find("price") != -1
                            ):
                                if occur and occur in linear:
                                    inqs[k] = linear[occur]
                        else:
                            return linear
                    else:
                        inqs[k] = "rep"
        return inqs

    async def find_parent(self, record: dict, model: Any):
        print("Record found to be: \n", record)
        for m in self.models:
            if m != model:
                rel = relshp.check_if_model_contains_relations(m)
                if rel[0] == model.__tablename__:
                    if rel[1] not in [col.key for col in m.__table__.c]:
                        return await read_stmt.read_stmt(m, record[rel[1]])
        print("Checking through foreign keys due to no parent existence from models")
        for k in self.f_keys:
            if model.__tablename__ in self.f_keys[k]:
                return await read_stmt.read_stmt(model, record[k])
        return print("Found No condition matching parent attribute!!")

    async def check_if_update(self, record: dict, model: Any, tn: str):
        print(f"Beginning update check on {tn}....")
        exist = await read_stmt.check_if_update_or_new_entry(record, model)
        if exist:
            prev = await read_stmt.read_stmt_to_dict(exist)
            if self.check_inequality(prev, record):
                inqs = await self.find_update_values(
                    record, await read_stmt.read_stmt_to_dict(exist), tn
                )
                if inqs:
                    print("Inquired updates: \n", inqs)
                    if not isinstance(inqs, str):
                        if "id" in inqs:
                            return inqs
                        for k in record.keys():
                            if k in inqs:
                                if isinstance(inqs[k], str):
                                    if len(inqs[k]) == 1 and not isinstance(
                                        record[k], str
                                    ):
                                        record[k] = inqs[k] + str(record[k])
                        print(f"Updating model: {tn} with values: \n {record}")
                    return (exist, record)
                else:
                    raise ValueError("Failed to get any inquired update!!")
            return prev
        return None

    async def find_how_update_occurs(self, prev: dict, tn: str, nxt: dict):
        print("Finding how update occurs...")
        for m in self.models:
            if m.__tablename__ != tn:
                rel = relshp.check_if_model_contains_relations(m)
                if rel[0] == tn:
                    return await self.check_if_child_updated(
                        await read_stmt.read_stmt(m, prev["id"]), nxt, prev
                    )
        return None

    async def check_if_child_updated(
        self, records: list, act: dict, prev: dict, recursed: bool = False
    ):
        print("Checking if child is updated...")
        if records:
            for r in records:
                for k in r.keys():
                    if (
                        not k.endswith("id")
                        and not k.startswith(self.ts_flags)
                        and k in act
                        and isinstance(r[k], str)
                        and r[k] == act[k]
                    ):
                        if not r["updated"] and not r["created"]:
                            raise ValueError(
                                f"Malformed db entries in table with data: \n {r}"
                            )
                        elif self.check_inequality(prev, act, r):
                            if self.compare_ts(r, prev):
                                return await self.check_manner_of_upd_from_child(r, act)
                            for f in self.f_keys.keys():
                                if f in r:
                                    return await self.find_if_parent_data_incs_excpt_of_key(
                                        self.f_keys[f], act, prev if recursed else r
                                    )
        return None

    async def find_if_parent_data_incs_excpt_of_key(
        self, table_names: list, act: dict, prev: dict
    ) -> str | None:
        for tn in table_names:
            for m in self.models:
                if m.__tablename__ == tn:
                    for c in m.__table__.c:
                        if not c.foreign_keys and c.key in act:
                            if not tn.startswith(self.tn_flags) and not tn.startswith(
                                ("inven", "sal")
                            ):
                                if not tn.startswith(self.user_flags):
                                    raise ValueError(
                                        f"Invalid model passed as parent with tablename: {tn} "
                                    )
                            return await self.check_if_record_exist_in_rel(m, act, prev)
        return None

    async def check_if_record_exist_in_rel(
        self, model: Any, act: dict, prev: dict
    ) -> str:
        print(
            f"Checking relship btw parent of {model.__name__} and its relative model..."
        )
        p_rec = await self.find_parent(prev, model)
        if not p_rec:
            raise ValueError(f"Failed to find any parent model with data: \n {prev}")

        for m in self.models:
            if m != model:
                rel = relshp.check_if_model_contains_relations(model)
                if rel[1] in self.f_keys and m.__tablename__ in self.f_keys[rel[1]]:
                    records = await read_stmt.read_stmt(m, prev["id"])
                    if records:
                        for r in records:
                            for k in r.keys():
                                if (
                                    not k.endswith("id")
                                    and not k.startswith(self.ts_flags)
                                    and isinstance(r[k], str)
                                ):
                                    if k in act and act[k] == r[k]:
                                        print(f"Found data within query...\n{r}")
                                        if self.compare_ts(r, p_rec):
                                            if (
                                                self.compare_ts(r, prev)
                                                or self.compare_ts(prev, p_rec)
                                                or r[rel[1]] in act.values()
                                            ):
                                                return "deduct"
                                            return "add"
                                        elif (
                                            self.compare_ts(prev, p_rec)
                                            or self.compare_ts(r, prev)
                                            and r[rel[1]] in act.values()
                                        ):
                                            return "deduct"
                                        return "add"
        return "add"

    def check_inequality(self, p_rec: dict, nxt: dict, c_rec: dict = None):
        for k in nxt.keys():
            if not k.endswith("id") and not k.startswith(self.ts_flags):
                if (
                    k in p_rec
                    and p_rec[k] != nxt[k]
                    or c_rec
                    and k in c_rec
                    and c_rec[k] != nxt[k]
                ):
                    return True
        return False

    @staticmethod
    def compare_ts(r: dict, p_rec: dict):
        if (
            r[("updated" if r["updated"] else "created")]
            > p_rec[("updated" if p_rec["updated"] else "created")]
        ):
            return True
        return False

    async def check_manner_of_upd_from_child(self, upd: dict, record: dict, tn: str):
        print("Checking manner to update with from child...")
        for k in upd.keys():
            if isinstance(upd[k], str):
                if k.endswith("id"):
                    for m in self.models:
                        if m.__tablename__ != tn:
                            rel = relshp.check_if_model_contains_relations(m)
                            if tn == rel[0]:
                                return self.check_if_child_updated(
                                    await read_stmt.read_stmt(m, upd[k]), record, upd
                                )
        return None

    @staticmethod
    def check_linear_update(act: int | float, inc: int | float) -> str | dict[str]:
        if inc:
            if 0.1 * act <= inc <= act * 2.0:
                if 0.7 * act > inc or inc > act * 1.3:
                    return {"add": "+", "deduct": "-"}
        return "replace"

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
