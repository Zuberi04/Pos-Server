from typing import Any

from utils.stmt import read_stmt
from utils.extras import MODELS, decode_json_objects, clean_str
from r_services.service import r_service


class FetchQueryData:
    def __init__(self):
        self.flags = ["ts", "id"]
        self.models = MODELS

    async def fetch_data(self, data: dict):
        res = await r_service.collect_cache(data["id"], data["name"])
        if res:
            res = decode_json_objects(res)
            upd = self.check_if_db_size_updated(data, res["size"])
            if not isinstance(upd, bool):
                raise ValueError(
                    f"Error, size of db not for model with name: {data['name']}"
                )
            elif not upd:
                return {data["name"]: res["data"]}
        for model in self.models:
            from utils.rel import relshp

            if clean_str(data["name"]) in clean_str(model.__name__):
                if not "id" in data:
                    return {"error": "No key to access data!!"}
                elif data["name"].startswith(("inv", "oper")):
                    return self.clean_data_for_response(
                        read_stmt.read_stmt(model, data["id"]), data, model
                    )
                return await self.find_n_model_data(
                    data, model, relshp.check_if_model_contains_relations(model)[0]
                )

        return {"error": "Invalid query to table!!"}

    async def find_n_model_data(
        self, data: dict, model: Any, p_tn: str, n_find: list = []
    ):
        cached = await r_service.collect_cache(data["id"], "inventory")
        if cached:
            cached = decode_json_objects(cached)
        else:
            from database.models import Inventory

            cached = read_stmt.read_stmt(Inventory, data["id"])

        if not cached:
            return {"error": "No data exist in rel to you!!"}
        elif not isinstance(cached, list):
            cached = [cached]

        def find_next_data(cached: list, m: Any, result: list = []):
            for c in cached:
                r = read_stmt.read_stmt(m, c["id"])
                if r:
                    if not isinstance(r, list):
                        result.append(r)
                    else:
                        result.extend(r)
            return result

        while p_tn != Inventory.__tablename__:
            from utils.rel import relshp

            for m in self.models:
                if m.__tablename == p_tn:
                    p_tn = relshp.check_if_model_contains_relations(m)[0]
                    n_find.append(model)
                    break
        n_find.insert(0, model)
        i = len(n_find) - 1
        while i:
            cached = find_next_data(cached, n_find[i])
            if not cached:
                raise ValueError("Failed to find n data!!")
            i -= 1

        return self.clean_data_for_response(cached, data, model)

    def check_if_db_size_updated(self, data: dict, size: int):
        for model in self.models:
            if model.__name__.lower() == data["name"]:
                if model().table_size() != size:
                    return True
                return False
        return None

    def clean_data_for_response(
        self, data: list | dict, creds: dict, model: Any = None, records: list = []
    ):
        if not data:
            return {"error": "No data exist in db for query sent"}
        elif not isinstance(data, list):
            data = [data]
        for record in data:
            records.append(read_stmt.delete_unneeded_data(record))
        if not model:
            r_service.cache_data(creds["id"], {creds["name"] + creds["q"]: records})
        else:
            r_service.cache_data(
                creds["id"],
                {creds["name"]: {"data": records, "size": model().table_size()}},
                3600,
            )
        return {data["name"]: records}

    async def collect_query(self, data: dict):
        from utils.extras import clean_data

        data = clean_data(data)
        res = await r_service.collect_cache(data["id"], data["name"] + data["q"])
        if res:
            return decode_json_objects(res)
        for model in self.models:
            if model.__name__.lower().strip() != data["name"]:
                continue
            res = read_stmt.read_stmt(model, query=data["q"])
            if not res:
                return {"error": f"No data exist in db for query {data['q']}"}
            elif "relshp" in data:
                return self.collect_nxt_data_in_query(data, res)
            return self.clean_data_for_response(res, data)
        return {"error": f"No data exist in db for query sent"}

    def collect_nxt_data_in_query(self, data: dict, res: dict | list):
        if not isinstance(res, list):
            res = [res]
        for model in self.models:
            names = [clean_str(model.__name__), clean_str(model.__tablename__)]
            if data["relshp"] in names:
                records = []
                for r in res:
                    r[data["relshp"]] = read_stmt.read_stmt(model, r["id"])
                    records.append(r)
                return self.clean_data_for_response(records, data)
        return self.clean_data_for_response(res, data)

    @staticmethod
    def fetch_user_profile(data: dict):
        from database.models import AdminUser

        res = read_stmt.read_stmt(AdminUser, query=data["id"])
        if res:
            return read_stmt.delete_unneeded_data(res)
        return {"error": "Failed to get profiled data!!"}

    @staticmethod
    def check_k_matches_cache(cache: dict, key: str):
        if not key in cache:
            return False
        return True


q_fetch = FetchQueryData()
