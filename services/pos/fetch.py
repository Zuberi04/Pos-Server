from utils.stmt import read_stmt
from utils.extras import MODELS, decode_json_objects
from r_services.service import r_service


class FetchQueryData:
    def __init__(self):
        self.flags = ["ts", "id"]
        self.models = MODELS

    async def fetch_data(self, data: dict):
        res = await r_service.collect_cache(data["id"])
        exist = self.check_k_matches_cache(res, data["name"])
        if exist:
            updated = await self.check_if_db_size_updated(data)
            if updated is None:
                raise ValueError(
                    f"Error, size of db not for model with name: {data['name']}"
                )
            elif not updated:
                return self.clean_data_for_response(
                    decode_json_objects(res[data["name"]])["data"]
                )

        for model in self.models:
            if data["name"].find("log") == -1:
                if data["name"].find("les", 2) == -1:
                    if data["name"].find("ory", 4) == -1:
                        return {"error": "Error, menu action not of type db action!!"}
                    elif model.__name__.lower() != data["name"]:
                        continue
                    res = read_stmt.read_stmt(model, query=data["id"])
                    if not res:
                        return {"error": "No data in model query for current user!!"}
                    r_service.cache_data(
                        data["id"],
                        {data["name"]: {"data": res, "size": model().table_size()}},
                    )
                    return self.clean_data_for_response(res)
                data["flag"] = data["name"]
                data["name"] = "catalog"

            elif model.__name__.lower() != "inventory":
                continue
            inv = read_stmt.read_stmt(model, query=data["id"])
            if not inv:
                return {"error": "No data in model query for current user!!"}
            r_service.cache_data(
                data["id"],
                {model.__name__.lower(): {"data": inv, "size": model().table_size()}},
            )
            return self.fetch_act_user_db_query(inv, data)
        return {"error": "Invalid query to table!!"}

    async def check_if_db_size_updated(self, data: dict):
        for model in self.models:
            if model.__name__.lower() != data["name"]:
                continue
            prev = await r_service.collect_cache(data["id"])
            prev = decode_json_objects(prev[data["name"]])
            if not "size" in prev or int(prev["size"]) != model().table_size():
                return True
            return False
        return None

    def fetch_act_user_db_query(self, res: list | dict, data: dict):
        print("Fetching data actual query!!")
        for model in self.models:
            if model.__name__.lower() != data["name"]:
                continue
            elif isinstance(res, dict):
                records = read_stmt.read_stmt(model, query=res["id"])
                if not records:
                    raise ValueError("Error, failed finding record from catalog!!")
                r_service.cache_data(
                    data["id"],
                    {data["name"]: {"data": records, "size": model().table_size()}},
                )
                return (
                    self.clean_data_for_response(records)
                    if not "flag" in data
                    else self.find_sales_in_data(records, data)
                )
            result = []
            for record in res:
                records = read_stmt.read_stmt(model, record["id"])
                if not records:
                    raise ValueError("Error, failed finding record from catalog!!")
                elif not isinstance(records, list):
                    if records not in result:
                        result.append(records)
                    continue
                elif records not in result:
                    result.extend(records)
                continue
            r_service.cache_data(
                data["id"],
                {data["name"]: {"data": result, "size": model().table_size()}},
            )
            return (
                self.clean_data_for_response(result)
                if not "flag" in data
                else self.find_sales_data(result, data)
            )
        return {"error": "Invalid query to table!!"}

    def find_sales_in_data(self, result: dict | list, data: dict):
        for model in self.models:
            if model.__name__.lower() != data["flag"]:
                continue
            if not isinstance(result, list):
                record = read_stmt.read_stmt(model, query=result["id"])
                if not record:
                    return {
                        "error": f"No sales record found for product {result} in inventory!!"
                    }
                r_service.cache_data(
                    data["id"],
                    {data["flag"]: {"data": record, "size": model().table_size()}},
                )
                return self.clean_data_for_response(record)
            records = []
            for res in result:
                record = read_stmt.read_stmt(model, query=res["id"])
                if not record:
                    continue
                elif record not in records:
                    records.append(record)
                continue
            r_service.cache_data(
                data["id"],
                {data["flag"]: {"data": records, "size": model().table_size()}},
            )
            return self.clean_data_for_response(records)
        return {"error": "Invalid query to table!!"}

    def clean_data_for_response(self, data: list | dict):
        records = []
        if isinstance(data, dict):
            return read_stmt.delete_unneeded_data(data)
        for record in data:
            if not record:
                continue
            record = read_stmt.delete_unneeded_data(record)
            if record not in records:
                records.append(record)
                continue
            continue
        return records

    def collect_query(self, data: dict):
        query = {}
        for k, v in data.items():
            if not isinstance(v, str):
                query[k] = v
                continue
            query[k] = v.lower().strip()
            continue

        for model in self.models:
            if model.__name__.lower().strip() != query["name"]:
                continue
            res = read_stmt.read_stmt(model, query=query["q"])
            if not res:
                return {"error": f"No data exist in db for query sent"}
            elif "relshp" in data:

                return self.collect_nxt_data_in_query(query, res)
            return self.clean_data_for_response(res)

        return {"error": f"No data exist in db for query sent"}

    def collect_nxt_data_in_query(self, data: dict, res: dict | list):
        for model in self.models:
            if model.__name__.lower() != data["relshp"]:
                if model.__tablename__ != data["relshp"]:
                    continue
            elif isinstance(res, dict):
                result = read_stmt.read_stmt(model, query=res["id"])
                if not result:
                    return self.clean_data_for_response(res)
                res[data["relshp"]] = result
                return self.clean_data_for_response(res)
            records = []
            for rec in res:
                result = read_stmt.read_stmt(model, query=rec["id"])
                if not result:
                    if rec not in records:
                        records.append(rec)
                    continue
                rec[data["relshp"]] = result
                if rec not in records:
                    records.append(rec)
                continue
            return self.clean_data_for_response(records)

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
