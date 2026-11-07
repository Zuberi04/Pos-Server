from services.pos.entries.process import proc_file


class FileEntries:
    def __init__(self):
        self.suffixes = [".xlxs", ".xls", ".docx", ".pdf", ".csv"]

    async def collect_file(self, data: dict, size: float = 0):
        if not data or not "data" in data or not data["data"]:
            return {"error": "No data passed for processing!"}
        from time import time, perf_counter

        start = time()
        for file in data["data"]:
            if not isinstance(file, dict):
                raise ValueError("Error: File passed is malformed")
            file["id"] = data["id"]
            size += file["size"] / 1024 / 1024
            await proc_file.detect_process_type(file)
        print(
            f"Done processing file entries with size: {size} with time :{(time() - start)}"
        )
        return {"msg": f"success processing file entries with size: {size}"}

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
