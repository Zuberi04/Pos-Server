from typing import Any
import datetime

from utils.stmt import read_stmt
from utils.normalize import norm_entries
from utils.extras import MODELS


class CheckNeedUpdate:
    def __init__(self):
        self.models = MODELS
        self.name_flags = {'name', 'names', 'productnames', 'productname', 'product-names', 'product', 'products'}

    def collect_prev_data_entries(self, model: Any, data: dict):
        # Checks through userid
        print("Beginning check for update from parent model....")
        n_rec = norm_entries.normalize_entries_based_on_model(model, data)
        print(f"Normalized entries are: {n_rec}")
        for k, v in n_rec.items():
            if k.find("_") != -1:
                record = read_stmt.read_stmt(model, v)
                if not record:
                    continue
                print('Found records from user id scanning records nxt....')
                return self.peruse_through_records(record, data, model, n_rec)
            continue
        return None

    def peruse_through_records(self, records: dict | list, data: dict, model, n_rec: dict):
        print("Beginning scan for query data...")

        if not isinstance(records, list):
            exist = self.check_where_record_exist(records, data, model)
            print(f'Exist value to be....{exist}')
            if exist is None:
                return None
            elif not exist['upd']:
                return exist
            stmt = self.fetch_stmt(n_rec, model)
            if not stmt:
                stmt = self.fetch_stmt(exist, model)
                if not stmt:
                    raise ValueError("Error, data not found for update")
            print("Stmt found to be: ", stmt)
            return stmt
        
        for rec in records:
            exist = self.check_where_record_exist(rec, data, model)
            print(f"Exist value to be....{exist}")
            if exist is None:
                continue
            elif not exist['upd']:
                return exist
            stmt = self.fetch_stmt(n_rec, model)
            if not stmt:
                stmt = self.fetch_stmt(exist, model)
                if not stmt:
                    raise ValueError('Error, data not found for update')
            print("Stmt found to be: ", stmt)
            return stmt

        return None

    @staticmethod
    def fetch_stmt(data: dict, model: Any):
        for key in data.keys():
            if key.find('id') != -1 and not key.find('_id') != -1:
                continue
            stmt = read_stmt.read_model_for_update_convinience(model, data[key])
            if not stmt:
                continue
            for k in data.keys():
                if k.find('id') != -1:
                    if stmt.id != data[k]:
                        continue
                    return stmt
                continue

        return None

    def check_where_record_exist(self, record: dict, data: dict, mod):
        # checks through use of parent id!
        print("Checking if query fits or update...")
        for k, v in record.items():
            if k == "id":
                for model in self.models:
                    if model.__name__ != mod.__name__:
                        rec = read_stmt.read_stmt(model, v)
                        if rec:
                            n_recs = norm_entries.normalize_entries_based_on_model(model, data, 'upd')
                            if not n_recs:
                                raise ValueError('Error, record not normalized for update check!!')
                            return self.find_if_same_data_exist(rec, n_recs)
                        continue
                    continue
                return None
            continue
        return None

    def find_if_same_data_exist(self, records: dict | list, data: dict):
        if not isinstance(records, list):
            return self.scan_through_values(records, data)

        for rec in records:
            if rec == data:
                return 'not required'
            print('Scanning through values...')
            exist = self.scan_through_values(rec, data)
            if not exist:
                continue
            print('Found exist to be true updating db...')
            return exist
        return None

    def scan_through_values(self, rec: dict, data: dict):
        print(f'Values received are: \n{rec} and next entrie: \n {data}')
        for k, v in rec.items():
            if k in data:
                if not isinstance(v, (float, int)):
                    print(f'Values passed are: {v} and {data[k]}')
                    if v != data[k]:
                        if isinstance(v, str):
                            continue
                    print(f'Update occurred with value...{v}')
                    return self.compare_norm_and_upd(rec, data)
                continue
            continue
        return None

    @staticmethod
    def compare_norm_and_upd(rec: dict, upd: dict):
        update = 0
        for k, v in rec.items():
            if k in upd:
                if v != upd[k]:
                    print(f'Values failed equality check: {v} and {upd[k]}')
                    update += 1
                    continue
                continue
            continue
        if update > 0:
            rec['upd'] = True 
        else: rec['upd'] = False
        return rec


req_update = CheckNeedUpdate()
