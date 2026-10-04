from services.pos.fetch import q_fetch
from r_services.service import r_service


class Accounts:
    def __init__(self):
        pass

    async def collect_data_to_process(
        self, data: dict, proc: list = [], flag: str = None, diff: float = None
    ):
        if not flag:
            cached = await r_service.collect_cache(data["id"], "accounts")
            if cached:
                graph = await r_service.collect_cache(data["id"], "graph")
                if graph:
                    from utils.extras import decode_json_objects

                    return {
                        "accounts": decode_json_objects(cached),
                        "graph": decode_json_objects(graph),
                    }
        else:
            data["name"] = flag
        inventory = await q_fetch.fetch_data(data)
        if not inventory or "error" in inventory:
            return {"error": "No records to balance your accounts!!"}
        elif isinstance(inventory, dict):
            inventory = [inventory]
        for record in inventory:
            if record:
                r = await q_fetch.collect_query(
                    {"name": "catalog", "q": record["id"], "relshp": "sales"}
                )
                if r and not "error" in r:
                    record["rels"] = r
                elif record not in proc:
                    proc.append(record)

        return (
            await self.diff_process_accounts_data(proc, data, diff)
            if not flag
            else proc
        )

    async def diff_process_accounts_data(
        self,
        procs: list,
        data: dict,
        diff: float = None,
        dr: dict = {"data": [], "total": 0},
        cr: dict = {"data": [], "total": 0},
    ):
        gp = 0
        for r in procs:
            if not "rels" in r and r not in dr["data"]:
                procs = [x for x in procs if x != r]
                r["credit"] = await q_fetch.collect_query(
                    {"name": "creditors", "q": r["id"]}
                )
                dr["data"].append(r)
                if r["credit"] and not "error" in r["credit"]:
                    if r["credit"] not in cr["data"]:
                        cr["data"].append(r["credit"])
                        cr["total"] += r["credit"]["amount"]
                dr["total"] += r["amount"]
            else:
                for x in r["rels"]:
                    x["credit"] = await q_fetch.collect_query(
                        {"name": "creditors", "q": x["id"]}
                    )
                    if "sales" in x and x not in cr["data"]:
                        x["owed"] = await q_fetch.collect_query(
                            {"name": "credited", "q": x["sales"]["id"]}
                        )
                        cr["data"].append(x["sales"])
                        cr["total"] += x["sales"]["amount"]
                        if x["owed"] and not "error" in x["owed"]:
                            if x["owed"] not in cr["data"]:
                                x["owed"]["owed"] = True
                                cr["data"].append(x["owed"])
                                cr["total"] += x["owed"]["amount"]
                        gp += self.calculate_gp_or_cog(x)
                    elif x not in dr["data"]:
                        dr["data"].append(x)
                        dr["total"] += self.calculate_gp_or_cog(x)
                        if not "sales" in x:
                            cr["data"].append(x)
                            cr["total"] += self.calculate_gp_or_cog(x)
                            procs = [y for y in procs if y != r]
                        elif x["credit"] and not "error" in x["credit"]:
                            if x["credit"] not in cr["data"]:
                                cr["data"].append(x["credit"])
                                cr["total"] += x["credit"]["amount"]
        expense = await self.collect_data_to_process(data, flag="expense")
        if expense:
            if isinstance(expense, dict):
                if not "error" in expense:
                    expense = [expense]
            for e in expense:
                if e not in cr["data"]:
                    gp -= e["amount"]
                    cr["data"].append(e)
                    cr["total"] += e["amount"]
        dr["data"].append({"profit": gp})
        dr["total"] += gp
        if cr["total"] != dr["total"]:
            if diff:
                if diff < 0:
                    cr["total"] += diff
                else:
                    dr["total"] -= diff
            elif cr["total"] != dr["total"]:
                return await self.collect_data_to_process(
                    data, diff=dr["total"] - cr["total"]
                )
        r_service.cache_data(
            data["id"], {"accounts": {"assets": dr, "credit": cr}}, 3600
        )
        from services.analysis.graph import gen_graph

        return {
            "accounts": {"assets": dr, "credit": cr},
            "analysis": await gen_graph.collect_req_data_for_graph(procs, data),
        }

    @staticmethod
    def calculate_gp_or_cog(x: dict):
        from utils.cog_pricing import est_price

        if "sales" in x:
            return x["sales"]["amount"] - (
                est_price.calculate_cog_from_r_price(
                    {y: x[y] for y in x.keys() if y != "sales"}
                )["amount"]
                * x["stock"]
                + x["owed"]["amount"]
                if "owed" in x and not "error" in x["owed"]
                else 0
            )
        return est_price.calculate_cog_from_r_price(x)["amount"] * x["stock"]


accounts = Accounts()
