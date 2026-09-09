from typing import Any

from utils.stmt import read_stmt
from utils.extras import MODELS
from utils.normalize import norm_entries
from utils.check_upd import req_update




class FindRelationBtwData:
    def __init__(self):
        self.models = MODELS
        self.flags = {"category", "creditors", "credits", "credited", "re-order"}
        self.price_flags = {
            "unitprice",
            "price",
            "prices",
            "unit-prices",
            "unit price",
            "unit prices",
            "unitprices",
        }
        self.stock_flags = {
            "stock",
            "warehouse",
            "shelfstock",
        }

    def check_if_rel_is_needed(self, record: dict, model: Any, extract: dict = None):
        print("Record to find rel: \n", record)
        print("Model found with values: \n", model)
        try:
            try:
                mod = model["model"]
            except KeyError:
                mod = model["m"]
        except Exception:
            mod = model

        if extract:
            tn , key = self.check_if_model_contains_relations(mod)
            if not key or not tn:
                raise ValueError('Error, failed to find foreign key for extracted data!!')
            
            record[key] = wrote['id'] if not key in wrote else wrote[key]
            return read_stmt.write_items_to_db(mod, norm_entries.normalize_entries_based_on_model(mod, record))
        elif mod.__name__.lower().find("inv" or 'expense') != -1:
            return self.write_inventory_data(mod, record)

        print(
            f"Checking if model passed contains relations....! for model: {mod.__name__}"
        )
        tn, key = self.check_if_model_contains_relations(mod)
        print(f"Key found for table with values: {tn} and {key}")
        if tn is None or not tn:
            raise ValueError("Model exist with no relations to others")
        wrote = self.find_belongs_to(tn, record, mod)
        if wrote is None or not wrote:
            raise ValueError("Error, failed to write data to db!!")
        elif 'upd' in wrote:
            return wrote
        
        record[key] = wrote["id"] if not key in wrote else wrote[key]

        return read_stmt.write_items_to_db(
            mod, norm_entries.normalize_entries_based_on_model(mod, record)
        )

    @staticmethod
    def check_if_model_contains_relations(model: Any):
        for col in model.__table__.c:
            if col.foreign_keys:
                for fk in col.foreign_keys:
                    return (fk.column.table.name, col.key)
                continue
            continue
        return None

    def find_belongs_to(self, tn: str, record: dict, mod: Any):
        for model in self.models:
            if model.__tablename__ == tn:
                stmt = req_update.collect_prev_data_entries(model, record)
                n_rec = norm_entries.normalize_entries_based_on_model(model, record)
                if stmt is None:
                    if tn.find("inven") != -1:
                        n_rec = self.find_whole_sale_price(n_rec, record)
                    return read_stmt.write_items_to_db(model, n_rec)
                elif not isinstance(stmt, dict):
                    print("Updating entries for stmt...\n", stmt)
                    if tn.find("inven") != -1:
                        n_rec = self.find_whole_sale_price(n_rec, record, stmt, mod)
                    return read_stmt.update_db_entries(stmt, n_rec)
                return stmt
        return None

    def find_whole_sale_price(
        self, n_rec: dict, record: dict, stmt: Any = None, mod: Any = None
    ):
        """w.p = (r.p * 0.8) * stock; where 1 reps total of retail price deducting 0.2 of max profit of a product at retail value"""
        if "stock" in n_rec:
            if "amount" in n_rec:
                for k in record.keys():
                    if k in self.price_flags:
                        if record[k] != n_rec["amount"]:
                            raise ValueError(
                                "Error, inequality failure from normalized data and original records"
                            )
                        n_rec["amount"] = (n_rec["amount"] * 0.8) * n_rec["stock"]
                        break
                    continue
            elif stmt:
                records = read_stmt.read_stmt(mod, query=stmt.id)
                if not records:
                    raise ValueError(
                        "Error, failed to find previous records from related model!!"
                    )
                elif not isinstance(records, list):
                    if "stock" in records:
                        if n_rec["stock"] != records["stock"]:
                            n_rec["stock"] += records["stock"]
                    elif not "amount" in n_rec:
                        n_rec["amount"] = (records["price"] * 0.8) * n_rec["stock"]
                    n_rec["amount"] += (records["price"] * 0.8) * n_rec["stock"]
                    return n_rec

                elif not "amount" in n_rec:
                    n_rec["amount"] = 0
                for rec in records:
                    rec = self.find_total_stock_of_p_from_data(rec, record)
                    n_rec["stock"] += rec["stock"]
                    n_rec["amount"] += (rec["price"] * 0.8) * rec["stock"]
                    continue
        return n_rec

    def find_total_stock_of_p_from_data(self, entry: dict, record: dict):
        prev = entry
        for k in prev.keys():
            if not isinstance(prev[k], str):
                continue
            for x, y in record.items():
                if prev[k] != y:
                    break
                print("Found data with value in record: ", prev[k])
                if x in self.stock_flags:
                    if "stock" in prev:
                        if prev["stock"] != record[x]:
                            prev["stock"] += record[x]
                        continue
                    prev["stock"] = record[x]
                    continue
                continue
            continue

        print(f"Returning stocks with value: {prev['stock']}")
        return prev

    @staticmethod
    def write_inventory_data(model: Any, record: dict):
        if not "user_id" in record:
            raise {
                "error": "Incomplete data passed with missing credentials as source!!"
            }
        rec = norm_entries.normalize_entries_based_on_model(model, record)
        return read_stmt.write_items_to_db(model, rec)


relshp = FindRelationBtwData()


