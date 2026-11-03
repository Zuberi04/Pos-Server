from typing import Any
from utils.extras import MODELS, clean_str, clean_data


class FindFitToModel:

    def __init__(self):
        self.models = MODELS

    @staticmethod
    def check_if_a_compares_b(a: str, b: str, k: int = 0):
        "b = 1 a== b = 1 else not b < b * 0.25"
        if a != b:
            for c in a:
                if c not in b and b.find(c) == -1:
                    k += 1
            if k < len(b) * 0.5 and len(a) * 0.5 > k < len(b) * 0.15:
                return True
            return False
        return True

    async def find_fit_via_filename(self, record: dict, name: str = None):
        if not name:
            return await self.find_similarity_in_columns(record)
        for model in self.models:
            names = [clean_str(model.__name__), clean_str(model.__tablename__)]
            for n in names:
                if self.check_if_a_compares_b(name, n):
                    return await self.find_similarity_in_columns(
                        record, model, model.__name__
                    )
        return await self.find_similarity_in_columns(record)

    async def find_fit_in_model_table_values(
        self, record: dict, infer: dict, w: int = 0
    ):
        print("Infered models from columns: \n", infer)
        if not "k" or not "m" in infer:
            return await self.find_similarity_in_columns(record)
        from utils.stmt import read_stmt

        data = await read_stmt.read_stmt(infer["m"])
        if data:
            if not isinstance(data, list):
                data = [data]
            for d in data:
                for k in infer["k"]:
                    for x in k.keys():
                        if x in d and k[x] in record:
                            if isinstance(d[x], str):
                                w += (
                                    1
                                    if self.check_if_a_compares_b(
                                        clean_str(d[x]),
                                        clean_str(record[k[x]]),
                                    )
                                    else -1
                                )
            w += infer["v"]
            if w and w < infer["v"] / len(infer["k"]):
                return await self.find_similarity_in_columns(record, infer["m"])
        print("Records before normalzation: \n", record)
        return await self.normalize_attr(infer, record)

    async def find_similarity_in_columns(
        self, record: dict, mod: Any = None, flag: str = None, result: list = []
    ):
        for model in self.models:
            r = {"m": model, "k": [], "v": 0}
            if mod:
                if mod == model:
                    if flag:
                        r["v"] += 1
                    else:
                        continue
            for col in model.__table__.c:
                if col.key != "id" and not col.key.endswith("ed"):
                    for k in record.keys():
                        if k != "id" and not k.endswith("ed"):
                            if self.check_if_a_compares_b(
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
        print("Models infered with values: \n", result)
        return await self.find_greatest_potential_of_exist(result, record, mod)

    async def find_greatest_potential_of_exist(
        self,
        result: list,
        record: dict,
        flag: Any = None,
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
            if not flag or flag != r["m"]:
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
        if len(infer["k"]) <= len(result) * 0.5:
            print("Recursion taking place due to infered cols <= 0.5 of len(to-infer)")
            return await self.find_greatest_potential_of_exist(
                result, record, infer["m"]
            )
        return await self.find_fit_in_model_table_values(record, infer)

    async def normalize_attr(self, infer: dict, record: dict, norm: dict = None):
        if not infer or not record:
            raise ValueError("Params missing for data normalization!!")
        elif not infer["k"] or not infer["m"]:
            return await self.find_similarity_in_columns(record)
        for k in infer["k"]:
            for x in k.keys():
                if not norm:
                    norm = {x: record[x if x in record else k[x]]}
                else:
                    norm[x] = record[x if x in record else k[x]]
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
