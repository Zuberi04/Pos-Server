from typing import Any
from utils.extras import MODELS, clean_str


class FindFitToModel:

    def __init__(self):
        self.models = MODELS
        self.flag: tuple = None

    @staticmethod
    def check_if_strings_compare(a: str, b: str):
        if len(a) != len(b):
            if len(a) > len(b):
                if a.find(b) != -1:
                    if len(a) - len(a.replace(b, "").strip()) == len(b):
                        return True
                return False
            elif b.find(a) != -1:
                if len(b) - len(b.replace(a, "").strip()) == len(a):
                    return True
            return False
        elif a != b:
            k = 0
            for char in a:
                if char not in b:
                    k += 1
            if k >= len(b) * 0.5:
                return False
        return True

    def find_fit_via_filename(self, record: dict, name: str = None):
        if not name:
            return self.find_similarity_in_columns(record)
        for model in self.models:
            names = [clean_str(model.__name__), clean_str(model.__tablename__)]
            for n in names:
                if self.check_if_strings_compare(name, n):
                    return self.find_similarity_in_columns(
                        record, model, model.__name__
                    )
        return self.find_similarity_in_columns(record)

    def find_fit_in_model_table_values(self, record: dict, infer: dict):
        if not "k" or not "m" in infer:
            return self.find_similarity_in_columns(record)

        from utils.stmt import read_stmt

        print("Model to infer: \n", infer)
        data = read_stmt.read_stmt(infer["m"])
        if not data:
            return self.normalize_attr(infer, record)
        elif not isinstance(data, list):
            data = [data]
        i = 0
        for d in data:
            c = 0
            for k in infer["k"]:
                for x in k.keys():
                    if x in d and k[x] in record:
                        if isinstance(d[x], str):
                            if self.check_if_strings_compare(
                                clean_str(d[x]),
                                clean_str(record[k[x]]),
                            ):
                                c += 1
                            else:
                                c -= 1
            i += (c / len(infer["k"])) / infer["v"]
            for k in record.keys():
                if k.endswith("_id"):
                    if k in d:
                        if self.check_if_strings_compare(
                            clean_str(record[k]), clean_str(d[k])
                        ):
                            i += 2 / infer["v"]
                        else:
                            i += 1 / infer["v"]
                    elif self.flag and k not in self.flag:
                        i -= 1 / infer["v"]
        if i + infer["v"] < infer["v"] * 0.75:
            return self.find_similarity_in_columns(record, infer["m"])
        return self.normalize_attr(infer, record)

    def find_similarity_in_columns(
        self, record: dict, mod: Any = None, flag: str = None, result: list = []
    ):
        for model in self.models:
            self.models = [m for m in self.models if m != model]
            r = {"m": model, "k": [], "v": 0}
            if flag and model.__name__ == flag:
                r["v"] += 1
            for col in model.__table__.c:
                if not col.key.endswith(("ed", "id")):
                    for k in record.keys():
                        if not k.endswith(("id", "ed")):
                            if self.check_if_strings_compare(
                                clean_str(k), clean_str(col.key)
                            ):
                                if {col.key: k} or {k: col.key} not in r["k"]:
                                    r["k"].append({col.key: k})
                                r["v"] += 1
            if r["k"] and r["v"]:
                try:
                    result[result.index(r["m"])]["k"].extend(
                        [
                            i
                            for i in r["k"]
                            if i not in result[result.index(r["m"])]["k"]
                        ]
                    )
                except ValueError:
                    result.append(r)

        print(f"Length of result: {len(result)}")
        if mod and not flag:
            from utils.rel import relshp

            self.flag = relshp.check_if_model_contains_relations(mod)
            result = [r for r in result if r["m"] != mod]
        print(f"Length of result after flag check: {len(result)}")
        return self.find_greatest_potential_of_exist(result, record, mod)

    def find_greatest_potential_of_exist(
        self,
        result: list,
        record: dict,
        flag: Any = None,
        infer: dict = None,
    ):
        def check_relshp_exist(model: Any, mod: Any):
            from utils.rel import relshp

            if model.__tablename__ == relshp.check_if_model_contains_relations(mod)[0]:
                return True
            return False

        for r in result:
            c = 0
            if flag and flag == r["m"]:
                continue
            elif r["v"]:
                if infer and len(infer["k"]) * 0.5 >= len(r["k"]):
                    if infer["m"] != r["m"]:
                        rel = check_relshp_exist(r["m"], infer["m"])
                        if not rel:
                            rel = check_relshp_exist(infer["m"], r["m"])
                            if not rel:
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
            return self.find_greatest_potential_of_exist(result, record, infer["m"])
        return self.find_fit_in_model_table_values(record, infer)

    def normalize_attr(self, infer: dict, record: dict):
        if not infer or not record:
            raise ValueError("Params missing for data normalization!!")
        elif not infer["k"] or not infer["m"]:
            return self.find_similarity_in_columns(record)
        norm = {}
        for k in infer["k"]:
            for x in k.keys():
                if k[x] in record:
                    norm[x] = record[k[x]]
        for k in record.keys():
            if not k in norm or record[k] not in norm.values():
                norm[clean_str(k)] = record[k]

        print("Norm attributes with values: \n", norm)
        return (infer, norm)

    def check_why_v_existed_toward_m(self, infer: dict, r_mod: dict, record: dict):

        def collect_cols(model: Any):
            return [col.key for col in model.__table__.c]

        for x in r_mod["k"]:
            if x not in infer["k"]:
                for y in x.keys():
                    for col in infer["m"].__table__.c:
                        if not col.key in record:
                            if not col.key.endswith("id"):
                                if x[y] in record:
                                    if isinstance(record[x[y]], col.type.python_type):
                                        if collect_cols(r_mod["m"]).index(
                                            y
                                        ) == collect_cols(infer["m"]).index(col.key):
                                            infer["k"].append({col.key: x[y]})
                                            record[col.key] = record[x[y]]
                                            print("Record with values: \n", record)
        return (infer, record)


find_fit_model = FindFitToModel()
