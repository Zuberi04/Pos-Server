import re

import pandas as pd
from pathlib import Path
from typing import Any

from utils.similarity import find_fit_model
from utils.rel import relshp
from utils.ext_data import residue_data


class ProcessFile:
    def __init__(self):
        self.process_types = {
            self.process_pdfs: {
                ".pdf",
            },
            self.process_image_file: {".png", ".jpeg", ".jpg"},
            self.process_using_dfs: {
                ".xlsx",
                ".xls",
                ".ods",
                ".json",
                ".csv",
                ".txt",
                ".tsv",
                ".sql",
                ".db",
            },
            self.process_dbs: {".accdb", ".odb", ".mdb"},
            self.process_docx: {
                ".docx",
                ".odt",
                ".doc",
            },
        }
        self.path = Path(__file__).parent.parent / "data_logs"
        self.path.mkdir(exist_ok=True)
        if not self.path.is_dir():
            raise ValueError("Error, path to data_logs dir not found!!")

    def detect_process_type(self, data: dict, ext: str = None):
        if not data:
            return {"error": "No data passed!!"}
        elif ext is None:
            data["path"] = self.path / f"{data['id'].split('-')[-1]}"
            data["path"].mkdir(exist_ok=True)
            data["path"] = data["path"] / f"{data['name']}"

        self.archive_file_sent(data)

        for k, v in self.process_types.items():
            if not callable(k):
                raise ValueError("Error: Instance is not callable!!")
            for item in v:
                if data["name"].endswith(item):
                    return k(data, item)
        return self.check_zipfile_for_pk(data)

    def process_pdfs(self, data: dict, flag: str = None):
        import pdfplumber as pdf

        with pdf.open(data["path"]) as df:
            c = 0
            res = []
            while c < len(df.pages):
                if not flag is None:
                    res.append(df[c].to_dict())
                    c += 1
                    continue

                table = df[c].extract_tables()
                if not table:
                    c += 1
                    continue
                procs = []
                t = 0
                while t < len(table):
                    proc = self.format_row_to_dict(table[0], table[t + 1])
                    if not proc:
                        raise ValueError("Error: Failed to format data to dict!!")
                    elif proc not in procs:
                        procs.append(proc)
                    t += 1
                res.extend(self.process_entries(procs, data["id"]))
                c += 1
            if not res:
                return self.process_pdfs(data, "extract")
            return res

    def process_dbs(self, data: dict):
        import pyodc
        from utils.stmt import read_stmt

        conn = pyodc.connect(
            r"DRIVER={MICROSOFT Access Driver (*.mdb, *.accdb)};" rf"BDQ={data['path']}"
        )
        cursor = conn.cursor()
        procs = []
        for row in cursor.fetchall():
            procs.append(read_stmt.read_stmt_to_dict(row))

        return self.process_entries(procs, data["id"])

    def process_using_dfs(self, data: dict, item: str, df: pd.DataFrame = None):
        from io import BytesIO

        buffer = BytesIO(data["file"])
        if item.endswith(("s", "x", "sb")):
            try:
                df = pd.read_excel(data["path"], engine="calamine")
            except Exception:
                df = pd.read_excel(buffer, engine="calamine")
        elif item.startswith(".js"):
            try:
                df = pd.read_json(data["path"], lines=False)
            except Exception:
                df = pd.read_json(buffer)
        elif item.startswith((".d", ".sq")):
            from database.config import engine

            try:
                df = pd.read_sql(data["path"], con=engine.connect())
            except Exception:
                df = pd.read_sql(buffer, con=engine.connect())
        else:
            try:
                df = pd.read_csv(data["path"])
            except Exception:
                df = pd.read_csv(buffer)

        if not len(df) or df is None:
            raise ValueError("Failed to create df structure from passed file!!")
        return self.process_entries(df.to_dict(orient="records"), data["id"])

    def archive_file_sent(self, data: dict, f: str = None):
        from hashlib import sha256
        import hmac

        if not isinstance(data["path"], Path):
            raise ValueError(
                f'User path for archive not found or not path type with val: {data["path"]}'
            )
        elif data["path"].is_file():
            a = sha256(
                Path(data["path"]).read_bytes(), usedforsecurity=False
            ).hexdigest()
            b = sha256(data["file"], usedforsecurity=False).hexdigest()
            if hmac.compare_digest(a, b):
                return print("File is of same dis-regarding copy!!")
            f = "ab"
        else:
            f = "wb"

        with data["path"].open(f"{f}") as file:
            file.write(data["file"])
        p = data["path"].parent
        if not p.is_dir():
            raise ValueError("Error: Parent path not a dir!!")
        if p.stat().st_size / (1024 * 2) >= 100:
            output = p.parent.parent.parent.resolve() / "zipped_logs"
            output.mkdir(exist_ok=True)
            output = output / p.name

            from zipfile import ZipFile as zip
            from os.path import relpath

            arcname = relpath(p, p.parent.resolve())
            with zip(output, "w", compresslevel=9) as zipf:
                zipf.write(p, arcname)
                from subprocess import run

                rm = run(["rm", "-rf", f"{p}"])
                if rm.stderr:
                    raise ValueError(
                        f"Error: Run error occured with value: {rm.stderr.decode('utf-8')}"
                    )
                return print(
                    f"Cleaned large dir with output: {rm.stdout.decode('utf-8')}"
                )

        return print("Archived file with success!!")

    def check_zipfile_for_pk(self, data: dict):
        from zipfile import is_zipfile, ZipFile
        from subprocess import run

        if not is_zipfile(data["file"]):
            return {"error": "File unsupported!!"}

        zip = ZipFile()

        path = self.path / "extracts"
        path.mkdir(exist_ok=True)
        zip.extractall(path, data["file"])
        res = []
        for p in path.iterdir():
            if p.is_file():
                data["file"] = p
                res.extend(self.detect_process_type(data, "zips"))
        run(["rm", "-rf", f"{path}"])
        return res

    def process_record_find_entry(self, record: dict):
        extracted = residue_data.extract_data(record)
        if not isinstance(extracted, list):
            if extracted is None:
                return relshp.check_if_rel_is_needed(record, self.find_model(record))
            elif "error" in extracted:
                return extracted
        wrote = relshp.check_if_rel_is_needed(record, self.find_model(record))
        if not wrote:
            raise ValueError(f"Error, wrote failed with value: {wrote}")
        ext = []
        for rec in extracted:
            w = relshp.check_if_rel_is_needed(
                self.clean_record(rec), self.find_model(rec), wrote
            )
            if w not in ext:
                ext.append(w)
            continue
        wrote["proc_ext"] = ext
        return wrote

    def process_entries(self, data: list, id: str):
        res = []
        for rec in data:
            if not "user_id" in rec:
                rec["user_id"] = id
            wrote = self.process_record_find_entry(self.clean_record(rec))
            if not wrote:
                raise ValueError(f"Error, failed to write to db with val: {wrote}")
            elif wrote not in res:
                res.append(wrote)
        return res

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

    def process_docx(self, data: dict):
        return None

    @staticmethod
    def clean_record(record: dict):
        rec = {}
        for k in record.keys():
            rec[k.lower().strip()] = None
            if not isinstance(record[k], str):
                if isinstance(record[k], dict):
                    for m in record[k].keys():
                        if isinstance(record[k][m], str):
                            rec[k][m.lower().strip()] = record[k][m].lower().strip()
                        else:
                            rec[k][m.lower().strip()] = record[k][m]

                else:
                    rec[k] = record[k]
            else:
                rec[k] = record[k].lower().strip()

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
