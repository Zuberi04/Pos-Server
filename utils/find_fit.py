from typing import Any
from utils.extras import MODELS, clean_str, clean_data, TS_FLAGS


class FindFitToModel:

    def __init__(self):
        self.models = MODELS
        self.ts_flags = TS_FLAGS

    @staticmethod
    def find_p(a: str, x: str, s: str = None):
        for c in x:
            if c in a and a.index(c) == x.index(c):
                s = c if not s else s + c if not c in s else s
        return len(s) / len(a) if s else 0

    @staticmethod
    def levenshtein_dist_mapper(splits: list, letters: str, q: str):
        result = set()
        for l, r in splits:
            for u in letters:
                if not q.index(u):
                    if r:
                        result.update([u + l[1:] + r])
                    result.update([u + l + r])
                else:
                    if len(l) != q.index(u):
                        if len(r) != q.index(u):
                            if len(l) > q.index(u):
                                result.update(
                                    [
                                        l[: q.index(u)] + u + l[q.index(u) + 1 :] + r,
                                        l[: q.index(u)] + u + l[q.index(u) :] + r,
                                    ]
                                )
                            elif len(r) > q.index(u):
                                result.update(
                                    [
                                        l + r[: q.index(u)] + u + r[q.index(u) + 1 :],
                                        l + r[: q.index(u)] + u + r[q.index(u) :],
                                    ]
                                )
                        else:
                            result.update([l[:-1] + u + r, l + u + r])
                    else:
                        result.update([l + r[:-1] + u, l + r + u])
        return result

    def extend_mapper(self, splits: list, letters: str, query: str):
        return {
            e2
            for e1 in self.levenshtein_dist_mapper(splits, letters, query)
            for e2 in self.levenshtein_dist_mapper(
                [(e1[:i], e1[i:]) for i in range(len(e1) + 1)], letters, query
            )
        }

    def find_word(
        self, query: str, splits: list, letters: str, edits: set = None, p: float = None
    ):
        if not edits:
            edits = self.levenshtein_dist_mapper(splits, letters, query)
        for e in edits:
            if query != e and not query in e or not e in query:
                if len(e) in range(len(query) - 2, len(query) + 2):
                    x = self.find_p(query, e)
                    if not p or p < x:
                        p = x
                        splits = [(e[i:], e[:i]) for i in range(len(e) + 1)]
                        for c in letters:
                            if c in e:
                                letters = letters.replace(c, "")
            else:
                print(f"{query} == {e}")
                return True
        print(f"Recursing with highest P of: {p} with unfound: {letters}")
        return (
            self.find_word(
                query, splits, letters, self.extend_mapper(splits, letters, query)
            )
            if letters and p
            else (
                True
                if not letters and p > (1 / len(query)) * (len(query) * 0.75)
                else False
            )
        )

    def check_if_a_compares_b(self, a: str, b: str, un_same: str = None):
        if a != b and not b in a or not a in b:
            if len(a) < len(b):
                return self.check_if_a_compares_b(b, a)
            for char in b:
                if char in a:
                    un_same = (
                        a.replace(char, "").strip()
                        if not un_same
                        else un_same.replace(char, "").strip()
                    )
            return (
                self.find_word(a, [(b[:i], b[i:]) for i in range(len(b) + 1)], un_same)
                if un_same
                else False
            )
        return True

    async def find_fit_via_filename(self, record: dict, name: str = None):
        if name:
            for model in self.models:
                names = [clean_str(model.__name__), clean_str(model.__tablename__)]
                for n in names:
                    if name == n:
                        return await self.find_similarity_in_columns(record, n)
        return await self.find_similarity_in_columns(record)

    async def find_fit_in_model_table_values(
        self, record: dict, infer: dict, w: int = 0
    ):
        print("Infered models from columns: \n", infer)
        if not infer or not "k" or not "m" in infer:
            return await self.find_similarity_in_columns(record)
        from utils.stmt import read_stmt

        data = await read_stmt.read_stmt(infer["m"])
        if data:
            data = [data] if not isinstance(data, list) else data
            for d in data:
                for i in range(len(infer["k"])):
                    for k in infer["k"][i].keys():
                        if k in d and isinstance(record[infer["k"][i][k]], type(d[k])):
                            if isinstance(d[k], str):
                                if not self.check_if_a_compares_b(
                                    d[k], record[infer["k"][i][k]]
                                ):
                                    w -= 1
                            w += 1
            if w < 0:
                print(f"W: {w}")
                return await self.find_similarity_in_columns(record, (infer["m"],))
        elif not w:
            return await self.why_exist_in_infer(record, infer)
        return await self.normalize_attr(infer, record)

    async def why_exist_in_infer(self, record: dict, infer: dict):
        nxt_inf, record = await self.find_similarity_in_columns(record, (infer["m"],))
        return self.check_why_v_existed_toward_m(nxt_inf, infer, record)

    async def find_similarity_in_columns(
        self, record: dict, excpt: tuple = None, flag: str = None, result: list = []
    ):
        for k in record.keys():
            if not k.endswith("id"):
                for m in self.models:
                    r = {"m": m, "k": [], "v": 0}
                    if excpt and m in excpt:
                        continue
                    elif flag and m.__tablename__ == flag:
                        r["v"] += 1
                    for col in m.__table__.c:
                        if not col.key.endswith("id") and not col.key.startswith(
                            self.ts_flags
                        ):
                            if self.check_if_a_compares_b(
                                clean_str(col.key), clean_str(k)
                            ):
                                r["k"].append({col.key: k})
                                r["v"] += 1
                    if r["v"] and r["k"]:
                        if not result:
                            result.append(r)
                        else:
                            for x in result:
                                if x["m"] == r["m"]:
                                    result = [y for y in result if y != x]
                                    r["k"].extend(
                                        [y for y in x["k"] if y not in r["k"]]
                                    )
                                    if len(r["k"]) > len(x["k"]):
                                        r["v"] += x["v"]
                            result.append(r)
        print("Models found with values: \n", result)
        return await self.find_greatest_potential_of_exist(result, record)

    @staticmethod
    def check_relshp_exist(models: list):
        from utils.rel import relshp

        for m in models:
            if (
                m.__tablename__
                == relshp.check_if_model_contains_relations(
                    models[-1 if not models.index(m) else 0]
                )[0]
            ):
                return True
        return False

    async def find_greatest_potential_of_exist(
        self, result: list, record: dict, infer: dict = None
    ):
        for r in result:
            if infer and infer["m"] != r["m"]:
                if len(infer["k"]) > len(r["k"]) and not self.check_relshp_exist(
                    [r["m"], infer["m"]]
                ):
                    infer, record = self.check_why_v_existed_toward_m(infer, r, record)
            else:
                for k in r["k"]:
                    for x in k.keys():
                        try:
                            if x or x.capitalize() in record:
                                r["v"] += r["k"].index(k) / len(r["k"]) * r["v"]
                            else:
                                r["v"] -= r["k"].index(k) / len(r["k"]) * r["v"]
                        except ZeroDivisionError:
                            if x or x.capitalize() in record:
                                r["v"] += r["v"] / len(r["k"])
                            else:
                                r["v"] -= r["v"] / len(r["k"])
            if not infer or r["v"] > infer["v"]:
                infer = r
        return await self.find_fit_in_model_table_values(record, infer)

    async def normalize_attr(self, infer: dict, record: dict, norm: dict = None):
        if not infer or not record:
            raise ValueError("Params missing for data normalization!!")
        elif not infer["k"] or not infer["m"]:
            return await self.find_similarity_in_columns(record)
        for k in infer["k"]:
            for x in k.keys():
                if k[x] in record:
                    if not norm:
                        norm = {x: record[k[x]]}
                    else:
                        norm[x] = record[k[x]]
        print("Normalized data: \n", norm)
        return (infer, self.fill_missing_v(record, norm))

    @staticmethod
    def fill_missing_v(record: dict, norm: dict):
        for k in record.keys():
            if not k in norm:
                norm[k] = record[k]
        print("Normalized with filled missings: \n", norm)
        return clean_data(norm)

    @staticmethod
    def collect_cols(model: Any):
        return [col.key for col in model.__table__.c]

    def check_why_v_existed_toward_m(self, infer: dict, r_mod: dict, record: dict):
        for x in r_mod["k"]:
            if x not in infer["k"]:
                for y in x.keys():
                    for col in infer["m"].__table__.c:
                        if not col.key in record:
                            if not col.key.endswith("id"):
                                if x[y] in record:
                                    if isinstance(record[x[y]], col.type.python_type):
                                        if self.collect_cols(r_mod["m"]).index(
                                            y
                                        ) == self.collect_cols(infer["m"]).index(
                                            col.key
                                        ):
                                            infer["k"].append({col.key: x[y]})
                                            record[col.key] = record[x[y]]
                                            print(
                                                "Record after why v existed towards model: \n",
                                                record,
                                            )
        return (infer, record)


find_fit_model = FindFitToModel()
