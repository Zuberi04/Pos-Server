from pathlib import Path


class AuditLogs:
    def __init__(self):
        self.audit_path = Path(__file__).parent.parent / "audits"
        if not self.audit_path.is_absolute():
            raise ValueError("Path is not absolute!!")
        self.audit_path.mkdir(exist_ok=True)

    @staticmethod
    def format_records(prev: dict, inc: dict, res: dict[str, dict] = None):
        for k in prev.keys():
            if k in inc:
                if not res:
                    res = {k: {"previous": prev[k], "current": inc[k]}}
                elif not k in res:
                    res[k] = {"previous": prev[k], "current": inc[k]}
        return res

    async def add_audit_log(
        self, inc: dict, user_id: str, name: str, prev: dict = None
    ):
        print("Starting to save audited logs...")
        if prev:
            for k in inc.copy().keys():
                if not k in prev:
                    del inc[k]
        path = self.audit_path / f"{user_id}"
        path.mkdir(exist_ok=True)
        path = path / f"{name}.csv"
        return await self.write_to_audit(
            path, self.format_records(prev, inc) if prev else inc, path.is_file()
        )

    @staticmethod
    async def write_to_audit(path: Path, rec: dict, upd: bool = False):
        with path.open("w" if not upd else "a") as w:
            from csv import DictWriter

            writer = DictWriter(w, fieldnames=rec.keys())
            if not upd:
                writer.writeheader()
            writer.writerow(rec)
            return print(
                f"{path.name} with a size: {path.stat().st_size / 1024/1024}mb"
            )


audit_log = AuditLogs()
