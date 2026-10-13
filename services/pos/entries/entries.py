from services.pos.entries.process import proc_file


class FileEntries:
    def __init__(self):
        self.suffixes = [".xlxs", ".xls", ".docx", ".pdf", ".csv"]

    async def collect_file(self, data: dict):
        if not data:
            return {"error": "File not passed for processing!"}
        size = 0
        res = []
        for file in data:
            if not isinstance(file, dict):
                raise ValueError("Error: File passed is malformed")
            size += file["size"] / 1024 / 1024
            res.extend(await proc_file.detect_process_type(file))

        return {"msg": f"Success Processing files with size: {size}"}

    async def add_entry_to_database(self, data: dict):
        if not "entries" in data:
            return {"error": "No entries sent to db for processing!!"}

        return await proc_file.process_entries(data)

    @staticmethod
    def clean_file_buffer(file: str | bytes):
        if not isinstance(file, bytes):
            if file.startswith("data:"):
                raw = file.split(",", 1)[1]
            raw += "=" * (-len(raw) % 4)
            return raw
        return file


entries = FileEntries()
