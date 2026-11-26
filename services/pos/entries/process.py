import pandas as pd
import time
from pathlib import Path

from utils.extras import clean_data, clean_str, MODELS


class ProcessFile:
    def __init__(self):
        self.flags = {"move", "movement", "movements"}
        self.models = MODELS
        self.check = {"type": {"in": "+", "out": "-"}}
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
            },
            self.process_dbs: {
                ".accdb",
                ".odb",
                ".mdb",
                ".sql",
                ".db",
            },
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

    async def detect_process_type(self, data: dict, ext: str = None):
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
                    return await k(data, item)
        return await self.check_zipfile_for_pk(data)

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

    async def process_pdfs(self, data: dict, flag: str = None):
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
                res.extend(await self.process_entries(procs, data, flag=False))
                c += 1
            if not res:
                return await self.process_pdfs(data, "extract")
            return res

    async def process_dbs(self, data: dict, procs: list = []):
        import pyodc
        from utils.stmt import read_stmt

        conn = pyodc.connect(
            r"DRIVER={MICROSOFT Access Driver (*.mdb, *.accdb)};" rf"BDQ={data['path']}"
        )
        for row in conn.cursor().fetchall():
            procs.append(await read_stmt.read_stmt_to_dict(row))
        return await self.process_entries(procs, data, flag=False)

    async def process_using_dfs(self, data: dict, item: str, df: pd.DataFrame = None):
        from io import BytesIO

        buffer = BytesIO(data["file"])
        if item.find(".") != -1:
            if not item.endswith(("sx", "lx", "ds")):
                if not item.endswith("json"):
                    if not item.endswith(("csv", "txt", "tsv")):
                        return {"error": "Type of file not able to process!!"}
                    df = pd.read_csv(buffer)
                else:
                    df = pd.read_json(buffer)
            else:
                df = pd.read_excel(buffer, engine="calamine", sheet_name=None)
            if not len(df) or df is None:
                raise ValueError(
                    "Failed to create df structure from passed file buffer!!"
                )
            elif not isinstance(df, pd.DataFrame):
                res = []
                for k in df.keys():
                    data["name"] = k
                    res.extend(
                        await self.process_entries(
                            df[k].to_dict(orient="records"), data, flag=False
                        )
                    )
                print(f"Len of res: {len(res)}")
                return res
            return await self.process_entries(
                df.to_dict(orient="records"), data, flag=False
            )
        return {"error": "Unsupported file type!!"}

    async def check_zipfile_for_pk(self, data: dict):
        from zipfile import is_zipfile, ZipFile
        from subprocess import run

        if not is_zipfile(data["path"]):
            return {"error": "File unsupported!!"}
        zip = ZipFile()

        path = self.path / "extracts"
        path.mkdir(exist_ok=True)
        zip.extractall(path, data["path"])
        res = []
        for p in path.iterdir():
            if p.is_file():
                data["path"] = p
                res.extend(await self.detect_process_type(data, "zips"))
        run(["rm", "-rf", f"{path}"])
        return res

    async def process_entries(
        self, data: list, entry: dict, res: list = None, flag: bool = False
    ):
        from setup import update_reqs

        entry["name"] = clean_str(update_reqs.format_q(entry["name"]))
        for f in self.flags:
            if f == entry["name"] or entry["name"].find(f) != -1:
                print(f"Flag {f} found in {entry['name']}!!")
                flag = True
                break
        for rec in data:
            rec["user_id"] = entry["id"]
            if flag:
                moved = await self.check_how_stock_mvment_occured(rec)
                if not moved:
                    continue
                rec = moved
            if res:
                res.append(
                    await self.process_record_find_entry(rec, clean_str(entry["name"]))
                )
            else:
                res = [
                    await self.process_record_find_entry(rec, clean_str(entry["name"]))
                ]
        print(f"Response with values: \n\t {res}")
        return res

    async def process_record_find_entry(self, record: dict, flag: str):
        from utils.rel import relshp

        print("Original record with value: \n\t", record)
        infer = await self.find_model(record, flag)
        if isinstance(infer, tuple):
            infer = await relshp.check_if_rel_is_needed(infer[1], infer[0]["m"])
            if not infer:
                raise ValueError(f"Error, writing to db failed failed!!")
        return infer

    @staticmethod
    def format_row_to_dict(key: tuple | list, row: tuple | list, record: dict = {}):
        if len(key) != len(row):
            raise ValueError("Error, key and rows length mismatch!!")
        keys = [clean_str(k) for k in key]
        print("Keys found with values: ", keys)
        rows = [clean_str(r) if isinstance(r, str) else r for r in row]
        for k in keys:
            record[k] = rows[keys.index(k)]
        print("Record dict created with value: \n", record)
        return record

    def process_image_file(self, data: dict):
        return None

    def process_docx(self, data: dict):
        return None

    @staticmethod
    async def find_model(record: dict, key: str = None):
        from utils.find_fit import find_fit_model

        result = await find_fit_model.find_fit_via_filename(record, key)
        if not result:
            raise ValueError(
                "Failed to find model based on record with vals:\n", record, key
            )
        return result

    async def check_how_stock_mvment_occured(self, record: dict):
        record = clean_data(record)
        for r in record.keys():
            if isinstance(record[r], str) and r in self.check:
                for m in self.models:
                    from utils.stmt import read_stmt

                    upd = await read_stmt.read_stmt_to_dict(
                        await read_stmt.check_if_update_or_new_entry(
                            record, m, "barcode"
                        )
                    )
                    if upd:
                        for u in upd.keys():
                            if isinstance(upd[u], int):
                                for v in record.keys():
                                    if isinstance(record[v], type(upd[u])):
                                        for w in self.check[r].keys():
                                            if w in clean_str(record[r]):
                                                upd[u] = int(
                                                    upd[u]
                                                    + float(
                                                        self.check[r][w]
                                                        + str(record[v])
                                                    )
                                                )
                                                return upd
        return print("Found not movement data!!")


proc_file = ProcessFile()
