import magic
import os
import openpyxl
import zipfile
from io import BytesIO
from typing import Any
import json
import ast


from utils.similarity import find_fit_model
from utils.rel import relshp
from utils.ext_data import residue_data


class ProcessFile:
    def __init__(self):
        self.mime_map = {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "text/csv": ".csv",
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "application/json": ".json",
        }
        self.path = ""

    def detect_file_type(self, data: dict):
        # print("File sent with data: ", data["file"])
        mime = magic.from_buffer(data["file"], mime=True)
        print("Mime passed with values: ", mime)
        if not mime:
            raise ValueError("file type not detected by magic-mime!!")
        ext = self.mime_map.get(mime)
        if not ext:
            ext = self.check_zipfile_for_pk(data["file"])
            if not ext:
                return {"error": "Invalid file received for imports"}
            elif ext == ".pptx":
                return {"error": "power point not supported by app!"}
        res = data
        res["ext"] = ext
        return self.archive_file_sent(res)

    def archive_file_sent(self, data: dict):
        os.makedirs("../data-logs", exist_ok=True)
        data["path"] = os.path.join(
            os.path.abspath("../data-logs"), f"{data['id'].split('-')[-1]}{data['ext']}"
        )

        with open(data["path"], "wb") as w:
            w.write(BytesIO(data["file"]).getvalue())
            return self.check_how_processing_occurs(data)

    def check_how_processing_occurs(self, data: dict):
        if not "ext" in data:
            raise ValueError("Error, file data passed without type detection!!")
        elif data["ext"] != ".xlsx":
            if data["ext"] != ".csv":
                if data["ext"] != ".docx":
                    if data["ext"] != ".json":
                        if ".png" or ".jpg" not in data["ext"]:
                            return self.process_file(data)
                        return self.process_image_file(data)
                    return self.process_json(data)
                return {"error": "Invalid file type sent for processing!!"}
            return self.process_csv(data)
        return self.process_sheets(data)

    @staticmethod
    def check_zipfile_for_pk(file: bytes):

        zf = zipfile.ZipFile(BytesIO(file))
        if not zf:
            raise ValueError("Error, file not processed by zipfile for detection!!")
        files = zf.namelist()
        for f in files:
            if f.find("word") != -1:
                return ".docx"
            elif f.find("ppt") != -1:
                return ".pptx"
            continue
        return None

    def process_json(self, data: dict):
        if not os.path.isfile(data["path"]):
            raise FileNotFoundError("Error, file passed not existing!!")

        with open(data["path"], "r") as file:
            try:
                records = json.load(file)
            except json.JSONDecodeError:
                records = ast.literal_eval(
                    data["file"].decode("utf-8", errors="replace")
                )

            if not records:
                raise ValueError("Error, failed reading json file!!")
            elif not isinstance(records, list):
                if not isinstance(records, dict):
                    return {"error": "Malformed data received from json file!!"}
                elif not "user_id" in records:
                    records["user_id"] = data["id"]
                return self.process_record_find_entry(records)
            print("Records from json file: \n", records)
            res = []
            for record in records:
                if not "user_id" in record:
                    record["user_id"] = data["id"]
                write = self.process_record_find_entry(record)
                if not write:
                    raise ValueError("Failed to write data to db!!")
                elif "error" in write:
                    continue
                elif write not in res:
                    res.append(write)
                continue
            return {"message": f"updated db with len{len(res)}"}

    def process_sheets(self, data: dict):
        try:
            buffer = BytesIO(data["file"])
            wb = openpyxl.load_workbook(buffer)
        except AttributeError:
            print("Import could not be resolved trying local csv processing!!")
            return self.process_file(data)
        if not wb:
            raise ValueError("Failed to read excel file!!")
        sheetnames = wb.sheetnames
        res = []
        for name in sheetnames:
            keys: tuple = None
            if name.lower().find("movement") != -1 or name.lower().find("sales") != -1:
                continue
            elif wb[name] != wb.active:
                continue
            for row in wb[name].iter_rows(values_only=True):
                if keys is None:
                    keys = row
                    print("Keys values are: ", keys)
                    continue
                elif keys[0] == row[0]:
                    continue
                record = self.format_row_to_dict(keys, row)
                if not record:
                    raise ValueError("Error, no record passed for processing!!")
                elif not "user_id" in record:
                    record["user_id"] = data["id"]
                wrote = self.process_record_find_entry(record)
                if "error" in wrote:
                    continue
                elif wrote not in res:
                    res.append(wrote)
                continue
            continue
        return res

    def process_record_find_entry(self, record: dict):
        extracted = residue_data.extract_data(record)
        if not isinstance(extracted, list):
            if extracted is None:
                return relshp.check_if_rel_is_needed(
                    self.clean_record(record), self.find_model(record)
                )
            elif "error" in extracted:
                return extracted
        wrote = relshp.check_if_rel_is_needed(record, self.find_model(record))
        if not wrote:
            raise ValueError(f"Error, wrote failed with value: {wrote}")
        ext = []
        for rec in extracted:
            w = relshp.check_if_rel_is_needed(rec, self.find_model(rec), wrote)
            if w not in ext:
                ext.append(w)
            continue
        wrote["proc_ext"] = ext
        return wrote

    def process_entries(self, data: dict):
        if not isinstance(data["entries"], list):
            if not "user_id" in data["entries"]:
                data["entries"]["user_id"] = data["id"]
            return self.process_record_find_entry(data["entries"])
        res = []
        for rec in data["entries"]:
            wrote = self.process_record_find_entry(rec)
            if not wrote:
                raise ValueError(f"Error, failed to write to db with val: {wrote}")
            elif "error" in wrote:
                continue
            elif wrote not in res:
                res.append(wrote)
            continue

        return {"message": f"updated db with len: {len(res)}"}

    @staticmethod
    def format_row_to_dict(key: tuple | list, row: tuple | list):
        record = {}
        if len(key) != len(row):
            raise ValueError("Error, key and rows length mismatch!!")
        keys = [k.lower().strip() for k in key]
        print("Keys found with values: ", keys)
        rows = [item for item in row]
        for k in keys:
            i = keys.index(k)
            record[k] = rows[i]
            continue
        for x, y in record.items():
            if isinstance(y, str):
                y = y.lower().strip()
            record[x] = y
            continue
        print("Record dict created with value: \n", record)
        return record

    def process_image_file(self, data: dict):
        return None

    def process_csv(self, data: dict):
        import csv

        if os.path.isfile(self.path):
            raise ValueError("Error, path not found!!")
        with open(self.path, "r") as f:
            reader = csv.reader(f, skipinitialspace=True)
            if not reader:
                raise ValueError("Error, reader contains no values from csv file!!")
            header: str = None
            keys: list = None
            model: Any = None
            for row in reader:
                if not header:
                    if len(row) <= 2:
                        for item in row:
                            if item.istitle():
                                header = "".join(row)
                                break
                            continue
                        continue
                    header = "".join(row)
                elif header in row:
                    continue
                elif not keys:
                    if len(row) > 2:
                        for item in row:
                            item = item.lower().strip()
                            if item.find("id") != -1:
                                keys = row
                                break
                            elif item.find("name") != -1:
                                keys = row
                                break
                            elif item.find("stock") != -1:
                                keys = row
                                break
                            elif item.find("price") != -1:
                                keys = row
                                break
                            continue
                        continue
                    continue
                elif row in keys:
                    continue
                record = self.format_row_to_dict(keys, row)
                if not "user_id" in record:
                    record["user_id"] = data["id"]
                while model is None:
                    model = find_fit_model.find_fit_via_filename(header)
                    if not model:
                        model = find_fit_model.find_fit_in_model_table_values(record)
                wrote = relshp.check_if_rel_is_needed(record, model)
                continue
            return {"message": f"imported data with length: {len(reader)}"}

        return None

    @staticmethod
    def clean_record(record: dict):
        rec = {}
        for k, v in record.items():
            k = k.lower().strip()
            if isinstance(v, str):
                rec[k] = v.lower().strip()
                continue
            rec[k] = v
            continue
        return rec

    @staticmethod
    def find_model(record: dict, key: str = None):
        model: Any = None
        while model is None:
            model = find_fit_model.find_similarity_in_columns(record)
            if not model:
                model = find_fit_model.find_fit_in_model_table_values(record)
                if not model:

                    model = find_fit_model.find_fit_via_filename(key)
                    if not model:
                        raise ValueError(
                            "Error, Failed to find model based on data given with vals: \t\n",
                            record,
                        )
        return model


proc_file = ProcessFile()
