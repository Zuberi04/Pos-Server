import datetime
from collections import deque

from utils.extras import MODELS
from utils.stmt import read_stmt
from services.pos.fetch import q_fetch
from utils.rel import relshp


class FindFitToModel:

    def __init__(self):
        self.models = MODELS

    def find_fit_via_filename(self, name: str):
        print(f"Name passed for check: {name}")
        for model in self.models:
            m_name = model.__name__.lower()
            if name.lower().strip() == m_name:
                return model
            elif name.lower().strip() == model.__tablename__.lower():
                return model
            fit = self.fit_p_of_model(m_name, name.lower().strip())
            if fit:
                return model
            continue
        return None

    @staticmethod
    def fit_p_of_model(m_name: str, name: str):
        count = 0
        for char in m_name:
            if char in name:
                count += 1
                continue
            continue
        p = count / len(m_name)
        if p >= 0.8:
            return True
        return False

    def find_fit_in_model_table_values(self, record: dict):
        for model in self.models:
            data = read_stmt.read_stmt(model)
            if not data:
                continue
            similar = self.check_if_data_compare(data, record)
            if not similar:
                continue
            return model
        return None

    def check_if_data_compare(self, data: list | dict, record: dict):
        if not isinstance(data, list):
            return self.compare_data(data, record)
        for rec in data:
            if isinstance(rec, list):
                return self.check_if_data_compare(rec, record)
            compare = self.compare_data(rec, record)
            if compare:
                return compare
            continue
        return False

    def compare_data(self, data: dict, record: dict):
        if data == record:
            return True
        history = [v for k, v in data.items() if isinstance(v, str)]
        recs = [v for k, v in record.items() if isinstance(v, str)]
        for k, v in data.items():
            if k in record:
                if isinstance(record[k], str):
                    s = self.check_if_strings_compare(v, record[k])
                    if s:
                        continue
                    return s
                continue
            elif v in record.values():
                return True
            continue
        return self.compare_list_values_from_both(history, recs)

    def compare_list_values_from_both(self, history: list, record: list):
        compare = 0
        for hist in history:
            if hist.find("-") != -1:
                if hist.count("-") == 4:
                    continue
            elif hist in record:
                compare += 1
                continue
            i = history.index(hist)
            while len(record) <= i:
                try:
                    rec = record[i]
                    s = self.check_if_strings_compare(hist, rec)
                    if s:
                        compare += 1
                    i += 1
                    continue
                except IndexError:
                    break

            continue
        if compare >= (len(history) * 0.5):
            return True
        return False

    @staticmethod
    def check_if_strings_compare(hist: str, data: str):
        if hist == data:
            return True
        same = 0
        un_same = 0
        for char in data:
            if char in hist:
                same += 1
                continue
            un_same += 1
            continue
        if same != un_same:
            if same > un_same:
                return True
            return False
        return True

    def find_similarity_in_columns(self, record: dict):
        result = []
        for model in self.models:
            for col in model.__table__.c:
                if col.key.find("id") != -1:
                    continue
                for k in record.keys():
                    if k != col:
                        if k.find(col.key) != -1:
                            result.append({"model": model, "key": k})
                            break
                        continue
                    result.append({"model": model, "key": k})
                    break
                continue
            continue
        print("columns found with similarities: \n", result)

        return self.check_why_similarity_occurred_in_columns(result, record)

    def check_why_similarity_occurred_in_columns(self, result: list, record: dict):
        proc = []
        for item in result:
            pr = {"model": item["model"]}
            print("Checking why similarity occured for item: \n", item)
            for k in item.keys():
                print(f"Key passed with value: {k}")
                if k == "model":
                    continue
                elif item[k] in record:
                    print(f"Starting check for key: {item[k]}")
                    if not isinstance(record[item[k]], (float, int)):
                        tn, key = relshp.check_if_model_contains_relations(
                            item["model"]
                        )
                        print("Foreign key found with values: ", key)
                        if tn:
                            exist = q_fetch.collect_query(
                                {
                                    "name": item["model"].__name__.lower(),
                                    "q": record[item[k]],
                                    "relshp": tn,
                                }
                            )
                        else:
                            exist = q_fetch.collect_query(
                                {
                                    "name": item["model"].__name__.lower(),
                                    "q": record[item[k]],
                                }
                            )
                        if exist:
                            if "error" in exist:
                                continue
                            pr["v_of_exist"] = [exist]
                            if pr not in proc:
                                proc.append(pr)
                                continue
                            i = proc.index(pr)
                            prev = proc[i]
                            if not isinstance(prev["v_of_exist"], list):
                                raise ValueError(
                                    "Error, malformed v of exist collected!!"
                                )
                            prev["v_of_exist"].extend(pr["v_of_exist"])
                            print("Prev updated with values: \n", prev)
                            proc[i] = prev
                            continue
                        continue
                    elif record[item[k]] > 0:
                        pr["v_of_e_num"] = {item[k]: record[item[k]]}
                        if pr not in proc:
                            proc.append(pr)
                        i = proc.index(pr)
                        prev = proc[i]
                        if prev["v_of_e_num"] != pr["v_of_e_num"]:
                            prev["v_of_e_num"].update(pr["v_of_e_num"])
                        proc[i] = prev
                        continue
                    continue
                continue

        print("Data found from check: \n", proc)

        return self.find_which_table_most_suit(proc, record)

    @staticmethod
    def find_p_from_values_exist(k: str, v: int | float, data: list):
        print("Checking through to find all models that contained int values!!")
        models = []
        for record in data:
            if not "v_of_e_num" in record:
                continue
            if k in record["v_of_e_num"]:
                if record["model"] not in models:
                    models.append(record["model"])
                continue
            continue
        return len(models) / v if len(models) > 1 else float(1)

    def find_which_table_most_suit(self, data: list, rec: dict):
        print("Check for which model suits most!!")
        infer = []
        for record in data:
            print("Beginning processing for each...")
            inf = {"m": None, "p": 0}
            if not isinstance(record, dict):
                raise ValueError("Error, data not of type dict!!")
            elif not "v_of_exist" in record:
                if not "v_of_e_num" in record:
                    raise ValueError(
                        f"Error, record contains no exist proof!! {record}"
                    )
                elif not isinstance(record["v_of_e_num"], dict):
                    raise ValueError(
                        f"Error, malformed value of exist passed with values: {record}"
                    )
                p = 0
                for k, v in record["v_of_e_num"].items():
                    p += self.find_p_from_values_exist(k, v, data)
                    if not p:
                        raise ValueError(
                            f'Error, failed to find p of exist from data{record["v_of_exist"]}'
                        )
                    continue
                inf = {"m": record["model"], "p": p}
                if inf not in infer:
                    infer.append(inf)
                    continue
                i = infer.index(inf)
                prev = infer[i]
                prev["p"] += inf["p"]
                infer[i] = prev
                continue
            elif not isinstance(record["v_of_exist"], list):
                raise ValueError(
                    f"Error, malformed value passed with type: {type(record['v_of_exist'])}"
                )
            print("Data with v of exist: \n", record["v_of_exist"])
            p = self.check_if_data_compare(record["v_of_exist"], rec)
            if not p:
                inf = {"m": record["model"], "p": -1}
            else:
                inf = {"m": record["model"], "p": 1}

            if inf not in infer:
                infer.append(inf)
                continue
            i = infer.index(inf)
            prev = infer[i]
            prev["p"] += inf["p"]
            continue

        return self.find_highest_p(infer)

    @staticmethod
    def find_highest_p(infer: list):
        print("Find highest infer from list: \n", infer)
        queue = Queue()
        print("Length of queue: ", queue.__len__())
        for i in infer:
            print("Popping item from queue...")
            if not queue.__len__():
                print("Adding first item to queue...")
                queue.push(i)
                continue
            prev = queue.pop()
            if prev == i:
                queue.push(i)
                continue
            elif prev["p"] < i["p"]:
                queue.push(i)
                continue
            queue.push(prev)
            continue

        if not queue.__len__():
            raise ValueError("Error. failed after proccessing to add any item to queue")
        return queue.pop()

    def find_p_of_reorder_level(self, rec: dict, value: int):
        if not "updated" in rec:
            return float(value * 2)
        elif not isinstance(rec["updated"], datetime.datetime):
            raise ValueError("Error, time object not of datetime!!")
        f = datetime.datetime.now() - rec["updated"]
        now = self.increase_time_delta()
        last_update = datetime.datetime.now() - f
        default: float = 0
        while now > last_update:
            if default <= 0:
                default += 6
            default += default * 0.65
            now = self.increase_time_delta(default)
        # theory if now that is last time of actual updates stock was at this level:
        # new stock would be the prev stock * f / now
        return value + (value * (f / now))

    @staticmethod
    def increase_time_delta(hours: float = None):
        if hours is None:
            return datetime.datetime.now()

        return datetime.datetime.now() - datetime.timedelta(hours=hours)


find_fit_model = FindFitToModel()


from typing import Any


class Queue:
    def __init__(self):
        self.queue = deque(maxlen=5)

    def push(self, data: Any):
        print("Data to push with value: ", data)
        if data in self.queue:
            return None
        return self.queue.appendleft(data)

    def pop(self):
        if not self.queue:
            raise ValueError("Error, popping item from empty queue!!")
        return self.queue.popleft()

    def __len__(self):
        return len(self.queue)
