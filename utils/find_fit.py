from typing import Any
from utils.extras import MODELS, clean_str, clean_data, TS_FLAGS


class FindFitToModel:

    def __init__(self):
        self.models = MODELS
        self.ts_flags = TS_FLAGS

    @staticmethod
    def find_p(a: str, x: str):
        return a == x or a in x

    @staticmethod
    async def levenshtein_dist_mapper(splits: list, letters: str):
        result = set()
        for l, r in splits:
            if r:
                result.update([l + r[1:]], [l + c + r[1:] for c in letters])
                if len(r) > 1:
                    result.update([l + r[1] + r[0] + r[2:]])
            result.update([l + c + r for c in letters])
        return result

    async def extend_mapper(self, edits: set, letters: str):
        return {
            e2
            for e1 in edits
            for e2 in await self.levenshtein_dist_mapper(
                [(e1[:i], e1[i:]) for i in range(len(e1) + 1)], letters
            )
        }

    async def find_word(
        self, query: str, splits: list, letters: str, edits: set = None, v: bool = False
    ):
        if not edits and not v:
            edits = await self.levenshtein_dist_mapper(splits, letters)
        for e in edits:
            if query != e:
                if len(e) in range(len(query) - 2, len(query) + 2) and self.find_p(
                    query, e
                ):
                    print(f"Probability eval with as equal: {query} == {e}")
                    return True
            else:
                print(f"Found {query} == {e}")
                return True
        return (
            await self.find_word(
                query, splits, letters, await self.extend_mapper(edits, letters), 1
            )
            if not v
            else not v
        )

    async def check_if_a_compares_b(self, a: str, b: str, un_same: str = None):
        if a != b:
            if len(a) < len(b):
                return await self.check_if_a_compares_b(b, a)
            for char in a:
                if char not in b:
                    un_same = char if not un_same else un_same + char
            return await self.find_word(
                a, [(b[:i], b[i:]) for i in range(len(b) + 1)], un_same
            )
        return True

    async def find_fit_via_filename(self, record: dict, name: str = None):
        if name:
            for model in self.models:
                names = [clean_str(model.__name__), clean_str(model.__tablename__)]
                for n in names:
                    if await self.check_if_a_compares_b(name, n):
                        return await self.find_similarity_in_columns(
                            record, (model,), model.__name__
                        )
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
            if not isinstance(data, list):
                data = [data]
            for d in data:
                for k in infer["k"]:
                    for x in k.keys():
                        if (
                            x in d
                            and k[x] in record
                            and isinstance(record[k[x]], type(d[x]))
                        ):
                            if isinstance(d[x], str):
                                w += (
                                    1
                                    if await self.check_if_a_compares_b(
                                        clean_str(d[x]),
                                        clean_str(record[k[x]]),
                                    )
                                    else -1
                                )
            w += infer["v"]
            if w and w < infer["v"] / len(infer["k"]):
                return await self.find_similarity_in_columns(record, (infer["m"],))
        print("Records before normalzation: \n", record)
        return await self.normalize_attr(infer, record)

    async def find_similarity_in_columns(
        self, record: dict, excpt: tuple = None, flag: str = None, result: list = []
    ):
        for model in self.models:
            r = {"m": model, "k": [], "v": 0}
            if excpt and model in excpt:
                if flag:
                    r["v"] += 1
                else:
                    continue
            for col in model.__table__.c:
                if col.key != "id" and not col.key.endswith("ed"):
                    for k in record.keys():
                        if k != "id" and not k.startswith(self.ts_flags):
                            if await self.check_if_a_compares_b(
                                clean_str(k), clean_str(col.key)
                            ):
                                if {col.key: k} and {k: col.key} not in r["k"]:
                                    r["k"].append({col.key: k})
                                    r["v"] += 1
            if r["k"] and r["v"]:
                if result:
                    for i in range(len(result)):
                        if result[i]["m"] == r["m"]:
                            result[i]["k"].extend(
                                [x for x in r["k"] if x not in result[i]["k"]]
                            )
                            r["add"] = True
                            break
                    if not "add" in r:
                        result.append(r)
                else:
                    result.append(r)
        return await self.find_greatest_potential_of_exist(result, record, excpt)

    async def find_greatest_potential_of_exist(
        self,
        result: list,
        record: dict,
        flag: tuple = None,
        infer: dict = None,
    ):
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

        for r in result:
            c = 0
            if not flag or r["m"] not in flag:
                if r["v"]:
                    if (
                        infer
                        and len(infer["k"]) * 0.5 > len(r["k"])
                        and infer["m"] != r["m"]
                    ):
                        if not check_relshp_exist([r["m"], infer["m"]]):
                            infer, record = self.check_why_v_existed_toward_m(
                                infer, r, record
                            )
                    else:
                        for k in r["k"]:
                            for x in k.keys():
                                c += 2 if x in record else 1
                        r["v"] *= c / len(r["k"])
                        if (
                            not infer
                            or infer["v"] < r["v"]
                            and len(infer["k"]) < len(r["k"])
                        ):
                            infer = r
        if len(infer["k"]) < len(result) * 0.5:
            return await self.find_greatest_potential_of_exist(
                result, record, (infer["m"],)
            )
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
        print("Norm with filled missings: \n", norm)
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


""" init_row = range(len(b) + 1)
        for i, x in enumerate(a):
            row = [i + 1]
            for j, y in enumerate(b):
                inserts = init_row[j + 1] + 1
                deletes = row[j] + 1
                substitutes = init_row[j] + (x != y)
                row.append(min(inserts, deletes, substitutes))
            init_row = row
        return init_row[-1]"""
