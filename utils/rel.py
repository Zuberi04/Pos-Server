from sqlite3 import IntegrityError
from typing import Any

from utils.find_fit import find_fit_model
from utils.stmt import read_stmt
from utils.extras import MODELS
from utils.cog_pricing import est_price


class FindRelationBtwData:
    def __init__(self):
        self.models = MODELS
        self.user_rel_m = ("inventory", "expense", "operation")

    async def check_if_rel_is_needed(self, record: dict, mod: Any, sleep: Any):
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
        wrote = await self.find_belongs_to(tn, record)
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
                        )
                    if infer["m"] in models:
                        models.remove(infer["m"])
                    print(f"Model found from infer: {infer['m']} parent of {m}:")
                    res.append(await self.update_write_or_return(infer["m"], record))
                    models.append(m)
                else:
                    res.append(await self.update_write_or_return(m, record))
        return res

    async def find_belongs_to(self, tn: str, record: dict):
        print("Table found with name: ", tn)
        if tn.endswith("ory"):
            record = est_price.calculate_cog_from_r_price(record)
        for model in self.models:
            if model.__tablename__ == tn:
                infer, record = await find_fit_model.find_similarity_in_columns(record)
                while infer["m"] != model:
                    print(f"Recursing due inquality model: {infer['m']}: {model}")
                    infer, record = await find_fit_model.find_similarity_in_columns(
                        record, (infer["m"],)
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
                        if not isinstance(linear, str):
                            occur = await self.find_how_update_occurs(prev, tn, record)
                            if occur and occur in linear:
                                if (
                                    not tn.startswith(self.tn_flags)
                                    or k.find("price") != -1
                                ):
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
            return prev
        return None

    async def find_how_update_occurs(self, prev: dict, tn: str, nxt: dict):
        print("Finding how update occurs...")
        for m in self.models:
            if (
                m.__tablename__ != tn
                and relshp.check_if_model_contains_relations(m)[0] == tn
            ):
                print(f"Checking if child-table was updated for table: {tn}")
                return await self.check_if_child_updated(
                    await read_stmt.read_stmt(m, prev["id"]), nxt, prev, m.__tablename__
                )
        return None

    async def check_if_child_updated(
        self, records: list, act: dict, prev: dict, tn: str, recursed: bool = False
    ):
        print(f"Checking if child is updated with records: \n {records}")
        if records:
            records = [records] if not isinstance(records, list) else records
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
                                return await self.check_manner_of_upd_from_child(
                                    r, act, tn
                                )
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
        for k in upd.keys():
            if isinstance(upd[k], str) and k.endswith("id"):
                for m in self.models:
                    if (
                        m.__tablename__ != tn
                        and tn == relshp.check_if_model_contains_relations(m)[0]
                    ):
                        return self.check_if_child_updated(
                            await read_stmt.read_stmt(m, upd[k]),
                            record,
                            upd,
                            m.__tablename__,
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
