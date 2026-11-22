from typing import Any

from utils.extras import MODELS, clean_str, clean_data, TS_FLAGS
import time


class FindFitToModel:

    def __init__(self):
        self.models = MODELS
        self.ts_flags = TS_FLAGS
        self.l = "abcdefghijklmnopqrstuvwxyz"

    def find_num_meaning(self, s: str, w: float = 0):
        from cmath import sqrt

        for c in s:
            if c in self.l and self.l.index(c):
                if s[s.index(c) - 1] in self.l and self.l.index(s[s.index(c) - 1]):
                    if self.l.index(s[s.index(c) - 1]) != self.l.index(c):
                        w += sqrt(
                            -(idx**2)
                            if self.l.index(s[s.index(c) - 1])
                            > (idx := self.l.index(c))
                            else idx**2 + self.l.index(s[s.index(c) - 1]) ** 2
                        )
        return w

    def compare_meaning_a_to_b(self, a: str, b: str):
        return len({self.find_num_meaning(clean_str(s), 0) for s in {a, b}}) == 1

    def fill_gaps(self, edit: str, missing: str, q: str):
        while len(edit) < len(q):
            for m in missing:
                if m in edit:
                    c = q.index(m) - edit.count(m)
                    if c:
                        if c < 0:
                            edit = "".join([e for e in edit if e != m])
                        else:
                            edit = edit[: q.index(m)] + m + edit[q.index(m) :]
                    else:
                        edit = self.re_arrange_edit(
                            [(a, b) for a, b in enumerate(q) if m == b], edit
                        )
                else:
                    edit = edit[: q.index(m)] + m + edit[q.index(m) :]
        return self.re_arrange_edit([(a, b) for a, b in enumerate(q)], edit) == q

    @staticmethod
    def re_arrange_edit(query: list, edit: str):
        edits = [(a, b) for a, b in enumerate(edit)]
        for a, b in edits:
            for x, y in query:
                if b == y and x != a:
                    if x < a:
                        edit = edit[:x] + b + edit[x:a] + edit[a + 1 :]
                    else:
                        edit = edit[:a] + edit[a + 1 : x] + b + edit[x:]
        return edit

    def check_if_a_compares_b(self, a: str, b: str, un_same: str = None):
        if len(a) >= len(b):
            if a != b:
                if len(a) > len(b) and a.find(b) != -1:
                    for char in a:
                        if b.find(char) == -1 or b.count(char) < a.count(char):
                            un_same = char if not un_same else un_same + char
                    return self.fill_gaps(b, un_same, a)
                return self.compare_meaning_a_to_b(a, b)
            return True
        return self.check_if_a_compares_b(b, a)

    async def find_fit_via_filename(self, record: dict, name: str = None):
        if name:
            for model in self.models:
                names = (model.__name__, model.__tablename__)
                for n in names:
                    if self.check_if_a_compares_b(clean_str(n), clean_str(name)):
                        return await self.find_similarity_in_columns(record, flag=n)
        return await self.find_similarity_in_columns(record)

    async def find_fit_in_model_table_values(self, result: list, record: dict):
        if result:
            from utils.rel import relshp, read_stmt, upd

            for r in result:
                data = await read_stmt.read_stmt(r["m"])
                if data:
                    data = [data] if not isinstance(data, list) else data
                    for d in data:
                        for k in d.keys():
                            for m in record.keys():
                                if isinstance(record[m], type(d[k])):
                                    if not isinstance(d[k], str):
                                        if {k: m} in r["k"]:
                                            r["v"] += 1
                                    else:
                                        if self.check_if_a_compares_b(d[k], record[m]):
                                            if {k: m} not in r["k"]:
                                                r["k"].append({k: m})
                                                r["v"] += 1
                                            for x in result:
                                                if x["m"] != r["m"]:
                                                    rel = relshp.check_if_model_contains_relations(
                                                        x["m"]
                                                    )
                                                    if rel[0] == r["m"].__tablename__:
                                                        for y in x["k"]:
                                                            for z in y.keys():
                                                                if z in upd.return_keys(
                                                                    record.keys()
                                                                ) and isinstance(
                                                                    record[
                                                                        key := (
                                                                            z
                                                                            if z
                                                                            in record
                                                                            else key.capitalize()
                                                                        )
                                                                    ],
                                                                    (float, int),
                                                                ):
                                                                    x["v"] += 1
            print("Infers after moving through table values: \n\t", result)
            return await self.find_greatest_potential_of_exist(
                sorted(result, key=lambda x: x["v"], reverse=True), record
            )
        return {"error": "Failed to find any model fitting the data!!"}

    async def find_similarity_in_columns(
        self, record: dict, excpt: tuple = None, flag: str = None, result: list = None
    ):
        for m in self.models:
            if not excpt or m not in excpt:
                r = {"m": m, "k": [], "v": 0}
                if flag == m.__tablename__:
                    r["v"] += 1
                for col in m.__table__.c:
                    if not col.key.endswith("id"):
                        for k in record.keys():
                            if (
                                not k.endswith("id")
                                and clean_str(col.key) == clean_str(k)
                                or self.check_if_a_compares_b(
                                    clean_str(col.key), clean_str(k)
                                )
                            ):
                                if len(r["k"]):
                                    for y in r["k"]:
                                        if not col.key in y:
                                            r["k"].append({col.key: k})
                                            r["v"] += 1
                                else:
                                    r["k"].append({col.key: k})
                                    r["v"] += 1
                if r["v"] and r["k"]:
                    r["v"] = len(r["k"]) - 1 if r["v"] > len(r["k"]) else r["v"]
                    if result:
                        for x in result:
                            if x["m"] == r["m"]:
                                result = [y for y in result if y != x]
                                r["k"].extend([y for y in x["k"] if y not in r["k"]])
                                if len(r["k"]) > len(x["k"]):
                                    r["v"] += x["v"]
                                break
                        result.append(r)
                    else:
                        result = [r]
        print("First inferences from columns only: \n\t", result)
        return await self.find_fit_in_model_table_values(result, record)

    @staticmethod
    async def why_infered(record: dict, infer: dict, count: int = 0):
        for i in range(len(infer["k"])):
            for col in infer["m"].__table__.c:
                if col.key in infer["k"][i] and isinstance(
                    record[infer["k"][i][col.key]], col.type.python_type
                ):
                    count += 1
                    from utils.rel import upd

                    if col.key in upd.return_keys(record.keys()):
                        count += 1
                    elif isinstance(record[infer["k"][i][col.key]], str):
                        count += count * 0.2
                else:
                    count -= 1
        return count

    async def find_greatest_potential_of_exist(
        self, result: list, record: dict, infer: dict = None
    ):
        print(f"Inferences on models include: \n {result}")
        for r in result:
            if not infer or r["m"] != infer["m"] and r["k"]:
                if infer and len(infer["k"]) != len(r["k"]):
                    infer, record = self.check_why_v_existed_toward_m(infer, r, record)
                elif len(r["k"]) == 1:
                    r["v"] += await self.why_infered(record, r, 0)
                from utils.rel import upd

                for k in r["k"]:
                    for x in k.keys():
                        if x in upd.return_keys(record.keys()):
                            r["v"] += r["v"] / len(r["k"])
                        else:
                            r["v"] -= r["v"] / len(r["k"])
                if not infer or r["v"] > infer["v"]:
                    infer = r
        print(f"Infered: \n\t {infer} \n\t From inferences: \n\t {result}")
        return (
            await self.normalize_attr(infer, record)
            if infer["v"] > len(infer["k"])
            else {"error": "not enough key-data to make any connection to model"}
        )

    async def normalize_attr(self, infer: dict, record: dict, norm: dict = None):
        if "k" and "m" in infer and record:
            for k in infer["k"]:
                for x in k.keys():
                    if not norm:
                        norm = {x: record[k[x]]}
                    else:
                        norm[x] = record[k[x]]
            return (infer, self.fill_missing_v(record, norm))
        return await self.find_similarity_in_columns(record)

    @staticmethod
    def fill_missing_v(record: dict, norm: dict):
        for k in record.keys():
            if not k in norm:
                norm[k] = record[k]
        return clean_data(norm)

    @staticmethod
    def collect_cols(model: Any):
        return [col.key for col in model.__table__.c]

    def check_why_v_existed_toward_m(self, infer: dict, r_mod: dict, record: dict):
        for x in r_mod["k"]:
            if x not in infer["k"]:
                for y in x.keys():
                    for col in infer["m"].__table__.c:
                        if not col.key.endswith("id") and not col.key.startswith(
                            self.ts_flags
                        ):
                            if not col.key in record:
                                if isinstance(record[x[y]], col.type.python_type):
                                    if self.collect_cols(r_mod["m"]).index(
                                        y
                                    ) == self.collect_cols(infer["m"]).index(col.key):
                                        if {col.key: x[y]} not in infer["k"]:
                                            infer["k"].append({col.key: x[y]})
        return (infer, record)


find_fit_model = FindFitToModel()
