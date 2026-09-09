class ExtractResidueData:
    def __init__(self):
        self.extract = {"credited", "creditor", "expenses", "assets"}

    def extract_data(self, record: dict):
        for k in record.keys():
            if k in self.extract:
                if not isinstance(record[k], list):
                    if not isinstance(record[k], str):
                        raise {"error": "Received malformed data from client!!"}
                    return self.check_if_contains_other_flags(record, k)
                return record[k]
            continue
        return None

    def check_if_contains_other_flags(self, record: dict, flagged: str):
        for k in record.keys():
            if k != flagged:
                if k in self.extract:
                    if not isinstance(record[k], list):
                        return {"error": "Received incomplete data from client!!"}
                    return record[k]
                continue
            continue
        return record


residue_data = ExtractResidueData()
