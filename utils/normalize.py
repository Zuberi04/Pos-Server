class NormalizeData:
    def __init__(self):
        self.flags = {
            "warehouse",
            "sku",
            "shelfstock",
            "total",
            "barcode",
        }
        self.catalog_flags = {
            "name",
            "names",
            "productnames",
            "productname",
            "product-names",
            "product",
            "products",
        }
        # check if name is alnum, check if name contains numeric, special chars, length of name

    def normalize_entries_based_on_model(self, model, data: dict, flag: str = None):
        cols = [{"k": col.key, "t": col.type} for col in model.__table__.c]
        m_name = model.__name__.lower()
        norm = data

        if model.__tablename__.find("log") != -1:
            print("Checking through catalog flags for fuzzy data... ")
            for flag in self.catalog_flags:
                if flag in norm.keys():
                    if "brand" in norm:
                        print(
                            f"Deleting data brand in favor of {flag} from passed record"
                        )
                        del norm["brand"]
                        break
                    norm["brand"] = norm[flag]
                    break
                continue

        print("Beginning normalization of data...")
        for col in cols:
            if flag:
                if col["k"].find("id") != -1:
                    cols.remove(col)
                continue
            elif not flag and col["k"] == "id":
                cols.remove(col)
                continue
            elif col["k"] in norm:
                cols.remove(col)
            continue

        if not cols:
            return norm

        return self.clear_excess_data(
            self.find_keys_that_contain_cols(cols, norm, m_name), model
        )

    def find_keys_that_contain_cols(self, cols: list, data: dict, m_name: str):
        entries = {}
        print("Columns with values: \n", cols)
        for col in cols:
            for k, v in data.items():
                if k.find("id") != -1:
                    continue
                elif k.find(col["k"]) != -1:
                    fit = self.find_fit_btw_keys(col["k"], k)
                    if not fit:
                        continue
                    elif isinstance(v, col["t"].python_type):
                        entries[col["k"]] = v
                        if col in cols:
                            cols.remove(col)
                        continue
                    continue
                continue
            continue
        data.update(entries)
        print("1. Norm of data with values: \n", data)
        if not cols:
            return data
        return self.find_remaining_cols_entries(cols, data, m_name)

    def find_remaining_cols_entries(self, cols: list, data: dict, m_name: str):
        left = {}
        for col in cols:
            if col["k"] == "mode" or col["k"] == "flag":
                continue
            for k, v in data.items():

                if isinstance(v, str):
                    if v.find("-") != -1:
                        if v.count("-") >= 4:
                            continue
                elif isinstance(v, col["t"].python_type):
                    if k in self.flags:
                        if not isinstance(v, (float, int)):
                            if k == "barcode":
                                if m_name.find("log", 3) != -1:
                                    left["id"] = v
                                    break
                                continue
                            elif k in self.catalog_flags:
                                fit = self.find_fit_btw_keys(col["k"], k)
                                if fit:
                                    left[col["k"]] = v
                                    if col in cols:
                                        cols.remove(col)
                                    break
                                continue
                        elif col["k"] == "stock":
                            if m_name.find("inv", 0, 4) != -1:
                                if k.find("shelf") != -1 or k.find("ware") != -1:
                                    if not col["k"] in left:
                                        left[col["k"]] = v
                                    elif left[col["k"]] != v:
                                        left[col["k"]] += v
                                    continue
                            elif m_name.find("log", 3) != -1:
                                if k.find("shelf") != -1:
                                    left[col["k"]] = v
                                    if col in cols:
                                        cols.remove(col)
                                    break
                                continue
                        elif k.find("tot") != -1:
                            if col["k"] != "amount":
                                continue
                            left[col["k"]] = v
                            if col in cols:
                                cols.remove(col)
                            break
                        continue
                    elif col in cols:
                        print(f"Col key {col['k']} with key passed: {k}")
                        if not isinstance(v, (float, int)):
                            fit = self.find_fit_btw_keys(col["k"], k)
                            if not fit:
                                continue
                            left[col["k"]] = v
                            if col in cols:
                                cols.remove(col)
                            continue
                        left[col["k"]] = v
                        if col in cols:
                            cols.remove(col)
                    continue
                continue
            continue
        data.update(left)
        print("2. Norm with values: \n", data)
        return data

    @staticmethod
    def find_fit_btw_keys(col_key: str, key: str):
        s = [char for char in col_key if char in key]
        u = [char for char in col_key if char not in key]
        if not s:
            return False
        elif not u:
            return True
        print("Found both similar and unsimilar letters")
        if len(s) >= len(u):
            return True
        return False

    def clear_excess_data(self, data: dict, model: any):
        cols = [{"k": col.key, "t": col.type} for col in model.__table__.c]
        res = {}
        for col in cols:
            if col["k"].find("id") != -1:
                continue
            elif col["k"] == "mode" or col["k"] == "flag":
                continue
            elif not col["k"] in data:
                for x, y in data.items():
                    if x.find('id') != -1 and x.find('_') == -1:
                        continue
                    if isinstance(y, col["t"].python_type):
                        if x in self.flags:
                            continue
                        elif x in self.catalog_flags:
                            if col["k"] == "brand":
                                data[col["k"]] = y
                                break
                            continue
                        fit = self.find_fit_btw_keys(col["k"], x)
                        if fit:
                            data[col["k"]] = y
                            break
                        continue
                    continue
            for k, v in data.items():
                if k.find("id") != -1:
                    if k.find('_') == -1:
                        continue
                elif col["k"] != k:
                    continue
                elif not isinstance(v, col["t"].python_type):
                    if not isinstance(v, int):
                        raise TypeError(f"Error, malformed value type on data: {v} for key {k} with type: {col['t'].python_type}")
                    v = float(v)
                res[k] = v
                continue
            continue

        print("Normalized attr for db is: \n", res)
        return res


norm_entries = NormalizeData()
