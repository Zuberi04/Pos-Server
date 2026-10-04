import pandas as pd
from pathlib import Path

from utils.extras import clean_str


class ProcessFile:
    def __init__(self):
        self.extracts = ["creditor", "credited"]
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
                res.extend(await self.process_entries(procs, data["id"]))
                c += 1
            if not res:
                return await self.process_pdfs(data, "extract")
            return res

    async def process_dbs(self, data: dict):
        import pyodc
        from utils.stmt import read_stmt

        conn = pyodc.connect(
            r"DRIVER={MICROSOFT Access Driver (*.mdb, *.accdb)};" rf"BDQ={data['path']}"
        )
        cursor = conn.cursor()
        procs = []
        for row in cursor.fetchall():
            procs.append(read_stmt.read_stmt_to_dict(row))

        return await self.process_entries(procs, data["id"])

    async def process_using_dfs(self, data: dict, item: str, df: pd.DataFrame = None):
        from io import BytesIO

        buffer = BytesIO(data["file"])
        if item.endswith(("s", "x", "sb")):
            try:
                df = pd.read_excel(data["path"], engine="calamine", sheet_name=None)
            except Exception:
                df = pd.read_excel(buffer, engine="calamine", sheet_name=None)

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
        elif not isinstance(df, pd.DataFrame):
            res = []
            for k in df.keys():
                print(f"Accessing key: {k}")
                data["name"] = k if isinstance(k, str) else data["name"]
                res.extend(
                    await self.process_entries(df[k].to_dict(orient="records"), data)
                )
            print(f"Len of res: {len(res)}")
            return res

        return await self.process_entries(df.to_dict(orient="records"), data)

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

    async def process_entries(self, data: list, entry: dict):
        res = []
        for rec in data:
            data = [r for r in data if r != rec]
            if not "user_id" in rec:
                rec["user_id"] = entry["id"]
            wrote = await self.process_record_find_entry(
                rec,
                entry["name"].split(".")[0] if "." in entry["name"] else entry["name"],
            )
            if not wrote:
                raise ValueError(f"Error, failed to write to db with val: {wrote}")
            res.append(wrote)

        return res

    async def process_record_find_entry(self, record: dict, flag: str):
        from utils.rel import relshp

        infer, norm = self.find_model(record, flag)
        wrote = await relshp.check_if_rel_is_needed(
            self.fill_missing_v_in_n(infer["k"], record, norm), infer["m"]
        )
        if not wrote:
            raise ValueError(f"Error, wrote failed with value: {wrote}")
        dep = self.extract_data(norm)  # extracts dependency data if found
        if not dep:
            return wrote
        elif isinstance(dep, dict):
            if "error" in dep:
                return (wrote, dep)
            dep = [dep]
        norm = {k: v for k, v in norm.items() if k != dep[1]}
        for rec in dep:
            rec.update(wrote)
            infer, norm = self.find_model(rec)
            norm = self.fill_missing_v_in_n(infer["k"], record, norm)
            w = await relshp.check_if_rel_is_needed(norm, infer["m"])
            if not "proc_deps" in wrote:
                wrote["proc_deps"] = [w]
            else:
                wrote["proc_deps"].append(w)

        return wrote

    def extract_data(self, record: dict):
        for k in record.keys():
            if k in self.extracts:
                if not isinstance(record[k], (list, dict)):
                    return {
                        "error": f"Malformed entries passed for dependency logging with key{k}!!"
                    }
                return (record[k], k)
        return None

    @staticmethod
    def format_row_to_dict(key: tuple | list, row: tuple | list):
        record = {}
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
    def find_model(record: dict, key: str = None):
        from utils.find_fit import find_fit_model

        result = find_fit_model.find_fit_via_filename(record, key)
        if not result:
            raise ValueError(
                "Failed to find model based on record with vals:\n", record, key
            )
        return result

    @staticmethod
    def fill_missing_v_in_n(keys: tuple, record: dict, norm: dict):
        for k in record.keys():
            if k not in keys:
                if not k in norm:
                    norm[clean_str(k)] = (
                        clean_str(record[k])
                        if isinstance(record[k], str)
                        else record[k]
                    )
        return norm


proc_file = ProcessFile()
