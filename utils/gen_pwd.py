from os import getenv
from pathlib import Path

from hashlib import shake_256
from random import choice

from dotenv import load_dotenv
from r_services.service import r_service

load_dotenv()

env = Path(".env")


class GenPassword:

    def __init__(self):
        self.chars = ["1234567890", '!@#$%^&*()_-+="']
        self.pwd_key = getenv("PWD_KEY", "POS-PWD:0001")

    async def gen_next_pwd_l(self, min_l=12, max_l=12 * 5 + 4):
        if not env.is_file():
            raise FileNotFoundError("Error, .env file is missing from root dir!!")
        exp = await r_service.collect_cache(self.pwd_key)
        if exp:
            return print("Expiry not met for alter pass!!")

        prev: list[str] = []
        with env.open("r") as r:
            data = r.readlines()
            if not data:
                raise ValueError("Error, no environ data found!!")
            data = [d for d in data if data.count(d) <= 1]
            for d in data:
                if not d.split("=")[0].endswith("PASSWORD"):
                    if not data.index(d):
                        env.write_text(f"{d}")
                    self._load_envs(d)
                else:
                    prev.append(d)

        for p in prev:
            if "=" not in p:
                raise ValueError("Error, malformed env variable passed!!")
            p = p.split("=")
            try:
                l = int((len(p[1]) / max_l) * min_l) + min_l
            except IndexError:
                l = min_l
            if p[0] not in self.chars:
                self.chars.append(p[0].capitalize())
            print(f"Gen password for key: {p[0]}")
            self._create_password(p[0], l)

        return r_service.cache_data(
            self.pwd_key, {"pos_db": "postgres"}, 3600 * 24 * 14
        )

    def _create_password(self, key: str, l: int):
        pwd = ""
        while len(pwd) < l:
            for item in self.chars:
                while len(pwd) in range(int(len(item) * 0.8 - 1)):
                    char = choice(item)
                    if char in pwd and pwd.count(char) < 3 or not char in pwd:
                        pwd = pwd + char

        return self._hash_password(key, pwd.encode("utf-8"), l)

    def _hash_password(self, key: str, pwd: bytes, l: int):
        return self._load_envs(key + "=" + shake_256(pwd).hexdigest(l * 2))

    def _load_envs(self, pwd: str):
        with env.open("a") as w:
            w.write(f"{pwd.strip()}\n")

        return print("Wrote to env with upd file size of: ", env.stat().st_size / 1024)


genpwd = GenPassword()
